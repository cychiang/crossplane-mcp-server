# This file hosts the MCP server implementation (moved from src/server.py)
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

# ... All MCP tool functions from server.py go here ...
# (Copy the tool functions from server.py)

if __name__ == "__main__":
    logger.info("crossplane-mcp-server running with stdio transport")
    mcp.run(transport='stdio')

