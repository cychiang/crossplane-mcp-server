# This file hosts the MCP server implementation (moved from src/server.py)
import logging
import sys
from typing import Dict, Any, List, Union, TypeAlias, Optional, Callable

from kubernetes import client, config
from typing_extensions import TypedDict, NotRequired

from mcp.server.fastmcp import FastMCP, Context

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


mcp = create_mcp_server()


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
    list_func: Callable[..., K8sObjectList],
    namespaced_list_func: Callable[..., K8sObjectList],
    namespace: Optional[str],
) -> Union[Dict[str, Any], ErrorResponse]:
    try:
        if namespace:
            resources = namespaced_list_func(
                group="apiextensions.crossplane.io",
                version="v1",
                namespace=namespace,
                plural=plural_name,
            )
        else:
            resources = list_func(group="apiextensions.crossplane.io", version="v1", plural=plural_name)
        items = resources.get("items", [])
        return {"success": True, resource_type: items, "count": len(items)}
    except client.rest.ApiException as e:
        logger.error(f"API error listing {resource_type}: {str(e)}")
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error listing {resource_type}: {str(e)}")
        return {"success": False, "error": str(e)}


async def _get_resource(
    resource_type: str,
    plural_name: str,
    name: str,
    get_func: Callable[..., K8sObject],
    namespaced_get_func: Callable[..., K8sObject],
    namespace: Optional[str],
) -> Union[Dict[str, Any], ErrorResponse]:
    try:
        if namespace:
            resource = namespaced_get_func(
                group="apiextensions.crossplane.io",
                version="v1",
                namespace=namespace,
                plural=plural_name,
                name=name,
            )
        else:
            resource = get_func(group="apiextensions.crossplane.io", version="v1", plural=plural_name, name=name)
        return {"success": True, resource_type: resource}
    except client.rest.ApiException as e:
        if e.status == 404:
            return {"success": False, "error": f"{resource_type.capitalize()} '{name}' not found"}
        logger.error(f"API error getting {resource_type}: {str(e)}")
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error getting {resource_type}: {str(e)}")
        return {"success": False, "error": str(e)}


@mcp.tool(description="List all Crossplane Compositions in the specified namespace or across all namespaces.")
async def list_compositions(context: Context) -> Union[ListCompositionsResponse, ErrorResponse]:
    return await _list_resources(
        resource_type="compositions",
        plural_name="compositions",
        list_func=k8s_client.list_cluster_custom_object,
        namespaced_list_func=k8s_client.list_namespaced_custom_object,
        namespace=context.get("namespace"),
    )


@mcp.tool(description="Get a specific Crossplane Composition by name.")
async def get_composition(context: Context, name: str) -> Union[GetCompositionResponse, ErrorResponse]:
    return await _get_resource(
        resource_type="composition",
        plural_name="compositions",
        name=name,
        get_func=k8s_client.get_cluster_custom_object,
        namespaced_get_func=k8s_client.get_namespaced_custom_object,
        namespace=context.get("namespace"),
    )


@mcp.tool(description="List all Crossplane CompositeResourceDefinitions (XRDs).")
async def list_xrds(context: Context) -> Union[ListXRDsResponse, ErrorResponse]:
    return await _list_resources(
        resource_type="xrds",
        plural_name="compositeresourcedefinitions",
        list_func=k8s_client.list_cluster_custom_object,
        namespaced_list_func=k8s_client.list_namespaced_custom_object,  # Not used, but required by helper
        namespace=None,
    )


@mcp.tool(description="Get a specific Crossplane CompositeResourceDefinition (XRD) by name.")
async def get_xrd(context: Context, name: str) -> Union[GetXRDResponse, ErrorResponse]:
    return await _get_resource(
        resource_type="xrd",
        plural_name="compositeresourcedefinitions",
        name=name,
        get_func=k8s_client.get_cluster_custom_object,
        namespaced_get_func=k8s_client.get_namespaced_custom_object,  # Not used, but required by helper
        namespace=None,
    )


@mcp.tool(description="List all Crossplane Claims (CompositeResourceClaims) across all namespaces.")
async def list_claims(context: Context) -> Union[ListClaimsResponse, ErrorResponse]:
    namespace = context.get("namespace")
    try:
        xrds_list: K8sObjectList = k8s_client.list_cluster_custom_object(
            group="apiextensions.crossplane.io", version="v1", plural="compositeresourcedefinitions"
        )
        all_claims: List[K8sObject] = []
        for xrd in xrds_list.get("items", []):
            if "claimNames" not in xrd.get("spec", {}):
                continue

            claim_plural = xrd["spec"]["claimNames"]["plural"]
            claim_group = xrd["spec"]["group"]
            claim_version = xrd["spec"]["versions"][0]["name"]

            if namespace:
                claims = k8s_client.list_namespaced_custom_object(
                    group=claim_group,
                    version=claim_version,
                    namespace=namespace,
                    plural=claim_plural,
                )
            else:
                claims = k8s_client.list_cluster_custom_object(
                    group=claim_group,
                    version=claim_version,
                    plural=claim_plural,
                )
            all_claims.extend(claims.get("items", []))

        return {"success": True, "claims": all_claims, "count": len(all_claims)}
    except client.rest.ApiException as e:
        logger.error(f"API error listing claims: {str(e)}")
        return {"success": False, "error": str(e)}
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
        if not composite_kind:
            xrds: K8sObjectList = k8s_client.list_cluster_custom_object(
                group="apiextensions.crossplane.io", version="v1", plural="compositeresourcedefinitions"
            )
            found_cr = False
            for xrd in xrds.get("items", []):
                for version in xrd.get("spec", {}).get("versions", []):
                    crd_kind = xrd.get("spec", {}).get("names", {}).get("kind")
                    if not crd_kind:
                        continue
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
                error_response: ErrorResponse = {"success": False, "error": f"CompositeResource '{composite_name}' not found"}
                return error_response
        else:
            xrds = k8s_client.list_cluster_custom_object(
                group="apiextensions.crossplane.io", version="v1", plural="compositeresourcedefinitions"
            )
            xrd = next((x for x in xrds.get("items", []) if x["spec"]["names"]["kind"] == composite_kind), None)
            if not xrd:
                error_response: ErrorResponse = {"success": False, "error": f"XRD for kind '{composite_kind}' not found"}
                return error_response

            cr = k8s_client.get_namespaced_custom_object(
                group=xrd["spec"]["group"],
                version=xrd["spec"]["versions"][0]["name"],
                namespace=composite_namespace,
                plural=xrd["spec"]["names"]["plural"],
                name=composite_name,
            )

        resource_refs = cr.get("status", {}).get("resourceRefs", [])
        managed_resources: List[K8sObject] = []
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
            except Exception as e:
                logger.error(f"Error fetching managed resource {ref}: {str(e)}")

        response: FindManagedResourcesResponse = {
            "success": True,
            "managed_resources": managed_resources,
            "count": len(managed_resources),
        }
        return response
    except client.rest.ApiException as e:
        if e.status == 404:
            error_response: ErrorResponse = {"success": False, "error": f"Composite resource '{composite_name}' not found."}
            return error_response
        logger.error(f"API error finding managed resources: {str(e)}")
        error_response: ErrorResponse = {"success": False, "error": str(e)}
        return error_response
    except Exception as e:
        logger.error(f"Unexpected error finding managed resources: {str(e)}")
        error_response: ErrorResponse = {"success": False, "error": str(e)}
        return error_response


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
        xrds_list: K8sObjectList = k8s_client.list_cluster_custom_object(
            group="apiextensions.crossplane.io", version="v1", plural="compositeresourcedefinitions"
        )
        xrds: List[K8sObject] = xrds_list.get("items", [])

        claim_xrd = next((xrd for xrd in xrds if xrd.get("spec", {}).get("claimNames", {}).get("kind") == claim_kind), None)
        if not claim_xrd:
            error_response: ErrorResponse = {"success": False, "error": f"No XRD found for claim kind '{claim_kind}'"}
            return error_response

        claim_plural = claim_xrd["spec"]["claimNames"]["plural"]
        claim_group = claim_xrd["spec"]["group"]
        claim_version = claim_xrd["spec"]["versions"][0]["name"]

        try:
            claim: K8sObject = k8s_client.get_namespaced_custom_object(
                group=claim_group, version=claim_version, namespace=namespace, plural=claim_plural, name=claim_name
            )
        except client.rest.ApiException as e:
            if e.status == 404:
                error_response: ErrorResponse = {"success": False, "error": f"Claim '{claim_name}' of kind '{claim_kind}' not found in namespace '{namespace}'"}
                return error_response
            raise

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
            response: DiagnoseClaimResponse = {"success": True, "diagnosis": diagnosis}
            return response

        xr_plural = claim_xrd["spec"]["names"]["plural"]
        xr_api_version = xr_ref["apiVersion"]
        xr_group, xr_version = xr_api_version.split("/")

        composite_resource: K8sObject = k8s_client.get_cluster_custom_object(
            group=xr_group, version=xr_version, plural=xr_plural, name=xr_ref["name"]
        )
        diagnosis["compositeResource"] = {
            "name": composite_resource["metadata"]["name"],
            "kind": composite_resource["kind"],
            "status": composite_resource.get("status", {})
        }
        analyze_conditions(composite_resource, f"Composite Resource '{composite_resource['metadata']['name']}'")

        managed_resources_details: List[K8sObject] = []
        mr_refs = composite_resource.get("status", {}).get("resourceRefs", [])
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
            except Exception as e:
                logger.error(f"Error fetching managed resource {ref['name']}: {str(e)}")
                summary.append(f"Could not fetch Managed Resource '{ref['name']}' ({ref['kind']}). Error: {str(e)}")

        diagnosis["managedResources"] = managed_resources_details

        if not summary:
            summary.append("All resources (Claim, XR, and MRs) are reporting a Ready status.")

        response: DiagnoseClaimResponse = {"success": True, "diagnosis": diagnosis}
        return response

    except client.rest.ApiException as e:
        error_message = f"Kubernetes API error: {e.reason} ({e.status})"
        logger.error(f"{error_message} - Body: {e.body}")
        error_response: ErrorResponse = {"success": False, "error": error_message, "details": e.body}
        return error_response
    except Exception as e:
        error_message = f"An unexpected error occurred: {str(e)}"
        logger.error(error_message, exc_info=True)
        error_response: ErrorResponse = {"success": False, "error": error_message}
        return error_response


if __name__ == "__main__":
    logger.info("crossplane-mcp-server running with stdio transport")
    mcp.run(transport='stdio')
