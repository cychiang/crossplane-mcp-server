import uvicorn
from server.main import app, logger, cache, k8s_client

if __name__ == "__main__":
    logger.info("Starting Kubernetes resource watcher...")
    cache.start_watching(k8s_client)

    logger.info("Starting crossplane-mcp-server with sse transport")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
