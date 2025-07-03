# This file hosts the MCP server implementation (moved from src/server.py)
import logging
import sys
from typing import Dict, Any, List, Union, TypeAlias, Optional, Callable

from kubernetes import client, config
from typing_extensions import TypedDict, NotRequired

from mcp.server.fastmcp import FastMCP, Context
from src.server import cache

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("crossplane-mcp-server")

# Type Aliases for Kubernetes objects for better readability
K8sObject: TypeAlias = Dict[str, Any]
K8sObjectList: TypeAlias = Dict[str, Any]


# TypedDicts for API responses to ensure consistent structure
class ErrorResponse(TypedDict):
    success: bool
    error: str
    details: NotRequired[str]


class ListCompositionsResponse(TypedDict):
    success: bool
    compositions: List[K8sObject]
    count: int


class GetCompositionResponse(TypedDict):
    success: bool
    composition: K8sObject


class ListXRDsResponse(TypedDict):
    success: bool
    xrds: List[K8sObject]
    count: int


class GetXRDResponse(TypedDict):
    success: bool
    xrd: K8sObject


class ListClaimsResponse(TypedDict):
    success: bool
    claims: List[K8sObject]
    count: int


class FindManagedResourcesResponse(TypedDict):
    success: bool
    managed_resources: List[K8sObject]
    count: int


class Diagnosis(TypedDict):
    claim: K8sObject
    compositeResource: NotRequired[K8sObject]
    managedResources: NotRequired[List[K8sObject]]
    summary: List[str]


class DiagnoseClaimResponse(TypedDict):
    success: bool
    diagnosis: Diagnosis


# Create MCP server instance
def create_mcp_server() -> 'FastMCP':
    """Create and return a FastMCP server instance."""
    return FastMCP(
        title="Crossplane MCP Server",
        description="An MCP server for interacting with Crossplane resources"
    )


from fastapi import FastAPI

app = FastAPI()

mcp = create_mcp_server()
app.mount("/mcp", mcp.run(transport="sse"))

@app.get("/health")
def health_check():
    return {"status": "ok"}


# Initialize Kubernetes client
def init_kubernetes_client() -> client.CustomObjectsApi:
    """Initialize and return a Kubernetes CustomObjectsApi client."""
    try:
        config.load_incluster_config()
        logger.info("Using in-cluster Kubernetes configuration")
    except config.ConfigException:
        try:
            config.load_kube_config()
            logger.info("Using kubeconfig file for Kubernetes configuration")
        except config.ConfigException:
            logger.error("Failed to load Kubernetes configuration")
            raise RuntimeError("No valid Kubernetes configuration found")
    return client.CustomObjectsApi()


k8s_client = init_kubernetes_client()


# Generic helper functions to reduce code duplication
async def _list_resources(
    resource_type: str,
    plural_name: str,
    namespace: Optional[str],
) -> Union[Dict[str, Any], ErrorResponse]:
    try:
        resource_cache = cache.get_cache().get(plural_name, {})
        if namespace:
            items = [
                item
                for item in resource_cache.values()
                if item.get("metadata", {}).get("namespace") == namespace
            ]
        else:
            items = list(resource_cache.values())
        return {"success": True, resource_type: items, "count": len(items)}
    except Exception as e:
        logger.error(f"Unexpected error listing {resource_type}: {str(e)}")
        return {"success": False, "error": str(e)}


async def _get_resource(
    resource_type: str,
    plural_name: str,
    name: str,
    namespace: Optional[str],
) -> Union[Dict[str, Any], ErrorResponse]:
    try:
        resource_cache = cache.get_cache().get(plural_name, {})
        key = f"{namespace}/{name}" if namespace else name
        resource = resource_cache.get(key)
        if resource:
            return {"success": True, resource_type: resource}
        else:
            return {"success": False, "error": f"{resource_type.capitalize()} '{name}' not found"}
    except Exception as e:
        logger.error(f"Unexpected error getting {resource_type}: {str(e)}")
        return {"success": False, "error": str(e)}


@mcp.tool(description="List all Crossplane Compositions in the specified namespace or across all namespaces.")
async def list_compositions(context: Context) -> Union[ListCompositionsResponse, ErrorResponse]:
    return await _list_resources(
        resource_type="compositions",
        plural_name="compositions",
        namespace=context.get("namespace"),
    )


@mcp.tool(description="Get a specific Crossplane Composition by name.")
async def get_composition(context: Context, name: str) -> Union[GetCompositionResponse, ErrorResponse]:
    return await _get_resource(
        resource_type="composition",
        plural_name="compositions",
        name=name,
        namespace=context.get("namespace"),
    )


@mcp.tool(description="List all Crossplane CompositeResourceDefinitions (XRDs).")
async def list_xrds(context: Context) -> Union[ListXRDsResponse, ErrorResponse]:
    return await _list_resources(
        resource_type="xrds",
        plural_name="compositeresourcedefinitions",
        namespace=None,
    )


@mcp.tool(description="Get a specific Crossplane CompositeResourceDefinition (XRD) by name.")
async def get_xrd(context: Context, name: str) -> Union[GetXRDResponse, ErrorResponse]:
    return await _get_resource(
        resource_type="xrd",
        plural_name="compositeresourcedefinitions",
        name=name,
        namespace=None,
    )


@mcp.tool(description="List all Crossplane Claims (CompositeResourceClaims) across all namespaces.")
async def list_claims(context: Context) -> Union[ListClaimsResponse, ErrorResponse]:
    namespace = context.get("namespace")
    try:
        claim_caches = cache.get_cache().get("claims", {})
        all_claims: List[K8sObject] = []
        for claim_plural_cache in claim_caches.values():
            for claim in claim_plural_cache.values():
                if not namespace or claim.get("metadata", {}).get("namespace") == namespace:
                    all_claims.append(claim)

        return {"success": True, "claims": all_claims, "count": len(all_claims)}
    except Exception as e:
        logger.error(f"Unexpected error listing claims: {str(e)}")
        return {"success": False, "error": str(e)}


@mcp.tool(description="Find managed resources referenced by a CompositeResource.")
async def find_managed_resources(
    context: Context,
    composite_name: str,
    composite_kind: str = "",
    composite_namespace: str = "default"
) -> Union[FindManagedResourcesResponse, ErrorResponse]:
    composite_namespace = context.get("namespace", composite_namespace)
    cr: K8sObject
    try:
        xrd_cache = cache.get_cache().get("compositeresourcedefinitions", {})
        
        if not composite_kind:
            # If kind is not specified, we have to search through all XRDs and live query for the CR.
            # This is because we don't cache all composite resources by default.
            # This can be improved by caching all CRs.
            xrds: K8sObjectList = k8s_client.list_cluster_custom_object(
                group="apiextensions.crossplane.io", version="v1", plural="compositeresourcedefinitions"
            )
            found_cr = False
            for xrd in xrds.get("items", []):
                for version in xrd.get("spec", {}).get("versions", []):
                    try:
                        cr = k8s_client.get_namespaced_custom_object(
                            group=xrd["spec"]["group"],
                            version=version["name"],
                            namespace=composite_namespace,
                            plural=xrd["spec"]["names"]["plural"],
                            name=composite_name,
                        )
                        found_cr = True
                        break
                    except client.rest.ApiException as e:
                        if e.status == 404:
                            continue
                        raise
                if found_cr:
                    break
            if not found_cr:
                return {"success": False, "error": f"CompositeResource '{composite_name}' not found"}
        else:
            xrd = next((x for x in xrd_cache.values() if x["spec"]["names"]["kind"] == composite_kind), None)
            if not xrd:
                return {"success": False, "error": f"XRD for kind '{composite_kind}' not found"}

            # Live query for the specific CR, as we don't cache them.
            try:
                cr = k8s_client.get_namespaced_custom_object(
                    group=xrd["spec"]["group"],
                    version=xrd["spec"]["versions"][0]["name"],
                    namespace=composite_namespace,
                    plural=xrd["spec"]["names"]["plural"],
                    name=composite_name,
                )
            except client.rest.ApiException as e:
                if e.status == 404:
                    return {"success": False, "error": f"Composite resource '{composite_name}' not found."}
                raise

        resource_refs = cr.get("status", {}).get("resourceRefs", [])
        managed_resources: List[K8sObject] = []
        # Live query for managed resources, as we don't cache them.
        for ref in resource_refs:
            try:
                mr_group, mr_version = ref["apiVersion"].split("/")
                mr_plural = ref["kind"].lower() + "s"
                mr_namespace = ref.get("namespace", composite_namespace)
                mr: K8sObject = k8s_client.get_namespaced_custom_object(
                    group=mr_group,
                    version=mr_version,
                    namespace=mr_namespace,
                    plural=mr_plural,
                    name=ref["name"],
                )
                managed_resources.append(mr)
            except client.rest.ApiException as e:
                if e.status != 404:
                    logger.warning(f"Error fetching managed resource {ref['name']}: {e.reason}")
            except Exception as e:
                logger.error(f"Unexpected error fetching managed resource {ref['name']}: {str(e)}")

        return {
            "success": True,
            "managed_resources": managed_resources,
            "count": len(managed_resources),
        }
    except client.rest.ApiException as e:
        logger.error(f"API error finding managed resources: {str(e)}")
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error finding managed resources: {str(e)}")
        return {"success": False, "error": str(e)}


@mcp.tool(description="Diagnose a Crossplane Claim by inspecting its Composite Resource and Managed Resources.")
async def diagnose_claim(
    context: Context,
    claim_name: str,
    namespace: str,
    claim_kind: str
) -> Union[DiagnoseClaimResponse, ErrorResponse]:
    """
    Diagnoses a Crossplane Claim by fetching the associated Composite Resource (XR)
    and all its Managed Resources (MRs), then summarizing their status conditions.
    """
    logger.info(f"Diagnosing claim '{claim_name}' in namespace '{namespace}' with kind '{claim_kind}'")

    try:
        xrd_cache = cache.get_cache().get("compositeresourcedefinitions", {})
        xrds: List[K8sObject] = list(xrd_cache.values())

        claim_xrd = next((xrd for xrd in xrds if xrd.get("spec", {}).get("claimNames", {}).get("kind") == claim_kind), None)
        if not claim_xrd:
            return {"success": False, "error": f"No XRD found for claim kind '{claim_kind}'"}

        claim_plural = claim_xrd["spec"]["claimNames"]["plural"]

        claim_cache_key = f"claims/{claim_plural}"
        claim_key = f"{namespace}/{claim_name}"
        claim = cache.get_cache().get(claim_cache_key, {}).get(claim_key)

        if not claim:
            return {"success": False, "error": f"Claim '{claim_name}' of kind '{claim_kind}' not found in namespace '{namespace}'"}

        diagnosis: Diagnosis = {
            "claim": {"name": claim["metadata"]["name"], "kind": claim["kind"], "status": claim.get("status", {})},
            "summary": []
        }
        summary: List[str] = diagnosis["summary"]

        def analyze_conditions(resource: K8sObject, resource_name: str) -> None:
            conditions = resource.get("status", {}).get("conditions", [])
            for cond in conditions:
                if cond.get("type") == "Ready" and cond.get("status") == "False":
                    summary.append(
                        f"{resource_name} is not ready. Reason: {cond.get('reason')}. Message: {cond.get('message')}"
                    )

        analyze_conditions(claim, f"Claim '{claim['metadata']['name']}'")

        xr_ref = claim.get("spec", {}).get("resourceRef")
        if not xr_ref:
            summary.append("Claim is not bound to a Composite Resource (XR).")
            return {"success": True, "diagnosis": diagnosis}

        xr_plural = claim_xrd["spec"]["names"]["plural"]
        xr_api_version = xr_ref["apiVersion"]
        xr_group, xr_version = xr_api_version.split("/")

        # Live query for the composite resource.
        try:
            composite_resource: K8sObject = k8s_client.get_cluster_custom_object(
                group=xr_group, version=xr_version, plural=xr_plural, name=xr_ref["name"]
            )
        except client.rest.ApiException as e:
            if e.status == 404:
                summary.append(f"Composite Resource '{xr_ref['name']}' not found.")
                return {"success": True, "diagnosis": diagnosis}
            raise

        diagnosis["compositeResource"] = {
            "name": composite_resource["metadata"]["name"],
            "kind": composite_resource["kind"],
            "status": composite_resource.get("status", {})
        }
        analyze_conditions(composite_resource, f"Composite Resource '{composite_resource['metadata']['name']}'")

        managed_resources_details: List[K8sObject] = []
        mr_refs = composite_resource.get("status", {}).get("resourceRefs", [])
        # Live query for managed resources.
        for ref in mr_refs:
            try:
                mr_group, mr_version = ref["apiVersion"].split("/")
                mr_plural = ref["kind"].lower() + "s"
                mr_namespace = ref.get("namespace")

                if mr_namespace:
                    mr: K8sObject = k8s_client.get_namespaced_custom_object(
                        group=mr_group, version=mr_version, namespace=mr_namespace, plural=mr_plural, name=ref["name"]
                    )
                else:
                    mr = k8s_client.get_cluster_custom_object(
                        group=mr_group, version=mr_version, plural=mr_plural, name=ref["name"]
                    )

                mr_detail: K8sObject = {
                    "name": mr["metadata"]["name"],
                    "kind": mr["kind"],
                    "status": mr.get("status", {})
                }
                managed_resources_details.append(mr_detail)
                analyze_conditions(mr, f"Managed Resource '{mr['metadata']['name']}' ({mr['kind']})")
            except client.rest.ApiException as e:
                if e.status != 404:
                    logger.warning(f"Error fetching managed resource {ref['name']}: {e.reason}")
                summary.append(f"Could not fetch Managed Resource '{ref['name']}' ({ref['kind']}). Error: {e.reason}")
            except Exception as e:
                logger.error(f"Unexpected error fetching managed resource {ref['name']}: {str(e)}")
                summary.append(f"Could not fetch Managed Resource '{ref['name']}' ({ref['kind']}). Error: {str(e)}")

        diagnosis["managedResources"] = managed_resources_details

        if not summary:
            summary.append("All resources (Claim, XR, and MRs) are reporting a Ready status.")

        return {"success": True, "diagnosis": diagnosis}

    except client.rest.ApiException as e:
        error_message = f"Kubernetes API error: {e.reason} ({e.status})"
        logger.error(f"{error_message} - Body: {e.body}")
        return {"success": False, "error": error_message, "details": e.body}
    except Exception as e:
        error_message = f"An unexpected error occurred: {str(e)}"
        logger.error(error_message, exc_info=True)
        return {"success": False, "error": error_message}


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting Kubernetes resource watcher...")
    cache.start_watching(k8s_client)

    logger.info("Starting crossplane-mcp-server with sse transport")
    uvicorn.run(mcp.app, host="127.0.0.1", port=8000, log_level="info")
