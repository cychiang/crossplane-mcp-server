import logging
import sys
from kubernetes import client, config
from typing import Optional, Dict, Any

from mcp.server.fastmcp import FastMCP, Context

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("crossplane-mcp-server")


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
        # Try to load in-cluster config first (for running inside a K8s pod)
        config.load_incluster_config()
        logger.info("Using in-cluster Kubernetes configuration")
    except config.ConfigException:
        # Fall back to kubeconfig file
        try:
            config.load_kube_config()
            logger.info("Using kubeconfig file for Kubernetes configuration")
        except config.ConfigException:
            logger.error("Failed to load Kubernetes configuration")
            raise RuntimeError("No valid Kubernetes configuration found")
    return client.CustomObjectsApi()


# Tools for interacting with Crossplane resources

@mcp.tool()
async def list_compositions(context: Context) -> Dict[str, Any]:
    """
    List all Crossplane Compositions in the specified namespace or across all namespaces.
    
    Returns:
        Dict containing the list of compositions
    """
    k8s_client = init_kubernetes_client()

    try:
        compositions = k8s_client.list_cluster_custom_object(
            group="apiextensions.crossplane.io",
            version="v1",
            plural="compositions"
        )

        return {
            "success": True,
            "compositions": compositions["items"],
            "count": len(compositions["items"])
        }
    except Exception as e:
        logger.error(f"Error listing compositions: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def get_composition(context: Context, name: str) -> Dict[str, Any]:
    """
    Get a specific Crossplane Composition by name.
    
    Args:
        name: Name of the composition
    
    Returns:
        Dict containing the composition details
    """
    k8s_client = init_kubernetes_client()

    try:
        composition = k8s_client.get_cluster_custom_object(
            group="apiextensions.crossplane.io",
            version="v1",
            plural="compositions",
            name=name
        )

        return {
            "success": True,
            "composition": composition
        }
    except client.rest.ApiException as e:
        if e.status == 404:
            return {
                "success": False,
                "error": f"Composition '{name}' not found"
            }
        else:
            logger.error(f"API error getting composition: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    except Exception as e:
        logger.error(f"Error getting composition: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def list_xrds(context: Context) -> Dict[str, Any]:
    """
    List all Crossplane CompositeResourceDefinitions (XRDs).
    
    Returns:
        Dict containing the list of XRDs
    """
    k8s_client = init_kubernetes_client()

    try:
        xrds = k8s_client.list_cluster_custom_object(
            group="apiextensions.crossplane.io",
            version="v1",
            plural="compositeresourcedefinitions"
        )

        return {
            "success": True,
            "xrds": xrds["items"],
            "count": len(xrds["items"])
        }
    except Exception as e:
        logger.error(f"Error listing XRDs: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def get_xrd(context: Context, name: str) -> Dict[str, Any]:
    """
    Get a specific Crossplane CompositeResourceDefinition (XRD) by name.
    
    Args:
        name: Name of the XRD
    
    Returns:
        Dict containing the XRD details
    """
    k8s_client = init_kubernetes_client()

    try:
        xrd = k8s_client.get_cluster_custom_object(
            group="apiextensions.crossplane.io",
            version="v1",
            plural="compositeresourcedefinitions",
            name=name
        )

        return {
            "success": True,
            "xrd": xrd
        }
    except client.rest.ApiException as e:
        if e.status == 404:
            return {
                "success": False,
                "error": f"XRD '{name}' not found"
            }
        else:
            logger.error(f"API error getting XRD: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    except Exception as e:
        logger.error(f"Error getting XRD: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def list_claims(context: Context) -> Dict[str, Any]:
    """
    List all Crossplane Claims (CompositeResourceClaims) across all namespaces.
    Returns:
        Dict containing the list of claims
    """
    k8s_client = init_kubernetes_client()
    try:
        claims = k8s_client.list_cluster_custom_object(
            group="apiextensions.crossplane.io",
            version="v1",
            plural="compositeresourceclaims"
        )
        return {
            "success": True,
            "claims": claims["items"],
            "count": len(claims["items"])
        }
    except Exception as e:
        logger.error(f"Error listing claims: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def find_managed_resources(context: Context, composite_name: str, composite_kind: str = "",
                                 composite_namespace: str = "default") -> Dict[str, Any]:
    """
    Find managed resources referenced by a CompositeResource.
    Args:
        composite_name: Name of the CompositeResource
        composite_kind: Kind of the CompositeResource (optional, e.g., 'CompositePostgreSQLInstance')
        composite_namespace: Namespace of the CompositeResource (default: 'default')
    Returns:
        Dict containing the managed resources referenced by the CompositeResource
    """
    k8s_client = init_kubernetes_client()
    try:
        # Try to get the composite resource (CR)
        if not composite_kind:
            # If kind is not provided, try to find it from XRDs
            xrds = k8s_client.list_cluster_custom_object(
                group="apiextensions.crossplane.io",
                version="v1",
                plural="compositeresourcedefinitions"
            )
            for xrd in xrds["items"]:
                for version in xrd.get("spec", {}).get("versions", []):
                    crd_kind = xrd["spec"].get("names", {}).get("kind")
                    if not crd_kind:
                        continue
                    try:
                        cr = k8s_client.get_namespaced_custom_object(
                            group=xrd["spec"]["group"],
                            version=version["name"],
                            namespace=composite_namespace,
                            plural=xrd["spec"]["names"]["plural"],
                            name=composite_name
                        )
                        composite_kind = crd_kind
                        break
                    except Exception:
                        continue
                if composite_kind:
                    break
            if not composite_kind:
                return {"success": False, "error": "CompositeResource kind not found"}
        else:
            # Try to find the XRD for the given kind
            xrds = k8s_client.list_cluster_custom_object(
                group="apiextensions.crossplane.io",
                version="v1",
                plural="compositeresourcedefinitions"
            )
            xrd = next((x for x in xrds["items"] if x["spec"]["names"]["kind"] == composite_kind), None)
            if not xrd:
                return {"success": False, "error": f"XRD for kind '{composite_kind}' not found"}
            group = xrd["spec"]["group"]
            version = xrd["spec"]["versions"][0]["name"]
            plural = xrd["spec"]["names"]["plural"]
            cr = k8s_client.get_namespaced_custom_object(
                group=group,
                version=version,
                namespace=composite_namespace,
                plural=plural,
                name=composite_name
            )
        # Find managed resources from resourceRefs
        resource_refs = cr.get("status", {}).get("resourceRefs", [])
        managed_resources = []
        for ref in resource_refs:
            try:
                mr = k8s_client.get_namespaced_custom_object(
                    group=ref["apiVersion"].split("/")[0],
                    version=ref["apiVersion"].split("/")[1],
                    namespace=ref.get("namespace", composite_namespace),
                    plural=ref["kind"].lower() + "s",  # crude pluralization
                    name=ref["name"]
                )
                managed_resources.append(mr)
            except Exception as e:
                logger.error(f"Error fetching managed resource {ref}: {str(e)}")
        return {
            "success": True,
            "managed_resources": managed_resources,
            "count": len(managed_resources)
        }
    except Exception as e:
        logger.error(f"Error finding managed resources: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


if __name__ == "__main__":
    logger.info("crossplane-mcp-server running with stdio transport")
    mcp.run(transport='stdio')
