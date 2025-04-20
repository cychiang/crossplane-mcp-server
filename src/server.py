import asyncio
import logging
import sys
import os
from typing import Dict, Any, List, Optional

from mcp.server.fastmcp import FastMCP, Context
from kubernetes import client, config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("crossplane-mcp-server")

# Create MCP server instance
mcp = FastMCP(
    title="Crossplane MCP Server",
    description="An MCP server for interacting with Crossplane resources"
)

# Initialize Kubernetes client
def init_kubernetes_client():
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
async def list_compositions(context: Context, namespace: Optional[str] = None) -> Dict[str, Any]:
    """
    List all Crossplane Compositions in the specified namespace or across all namespaces.
    
    Args:
        namespace: Optional namespace to filter compositions (None for all namespaces)
    
    Returns:
        Dict containing the list of compositions
    """
    k8s_client = init_kubernetes_client()
    
    try:
        if namespace:
            compositions = k8s_client.list_namespaced_custom_object(
                group="apiextensions.crossplane.io",
                version="v1",
                namespace=namespace,
                plural="compositions"
            )
        else:
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
async def get_composition(context: Context, name: str, namespace: Optional[str] = None) -> Dict[str, Any]:
    """
    Get a specific Crossplane Composition by name.
    
    Args:
        name: Name of the composition
        namespace: Optional namespace for the composition (None for cluster-scoped)
    
    Returns:
        Dict containing the composition details
    """
    k8s_client = init_kubernetes_client()
    
    try:
        if namespace:
            composition = k8s_client.get_namespaced_custom_object(
                group="apiextensions.crossplane.io",
                version="v1",
                namespace=namespace,
                plural="compositions",
                name=name
            )
        else:
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

# @mcp.resource("server://info")
# async def get_server_info(context: Context) -> Dict[str, Any]:
#     """
#     Get information about the Crossplane MCP server.
#
#     Returns:
#         Dict containing server information
#     """
#     return {
#         "name": "Crossplane MCP Server",
#         "version": "0.1.0",
#         "description": "A server that implements the Crossplane MCP API for interacting with Crossplane resources",
#         "supported_apis": [
#             "apiextensions.crossplane.io/v1/compositions",
#             "apiextensions.crossplane.io/v1/compositeresourcedefinitions"
#         ]
#     }

# async def main():
#     """Main entrypoint for running the MCP server"""
#     logger.info("Starting Crossplane MCP Server...")
#
#     # Define port from environment or use default
#     port = int(os.environ.get("MCP_SERVER_PORT", 8080))
#     host = os.environ.get("MCP_SERVER_HOST", "127.0.0.1")
#
#     try:
#         mcp.run()
#         # Start the server
#         # server = await mcp.start(host=host, port=port)
#         # logger.info(f"Crossplane MCP Server running on {host}:{port}")
#         #
#         # # Keep the server running until interrupted
#         # await server.serve_forever()
#     except KeyboardInterrupt:
#         logger.info("Shutting down Crossplane MCP Server...")
#     except Exception as e:
#         logger.error(f"Error running MCP server: {str(e)}")
#         sys.exit(1)

if __name__ == "__main__":
    mcp.run()
    # asyncio.run(main())
