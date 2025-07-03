# crossplane-mcp-server

A Python implementation of the Model Context Protocol (MCP) for Crossplane. This project enables LLMs and other clients to interact with Kubernetes and Crossplane resources (such as XRDs, Compositions, Claims, and Managed Resources) via a standardized protocol.

## Architecture

The server runs as a FastAPI web server and exposes an MCP endpoint over Server-Sent Events (SSE). It implements a caching layer (`src/server/cache.py`) that watches for changes in Kubernetes resources (Compositions, XRDs, and Claims) and stores them in memory. This significantly improves performance by reducing direct API calls to the Kubernetes server.

- The server is a FastAPI application that uses `uvicorn` for serving.
- The cache is populated by background threads that watch for resource changes.
- All tool functions in `src/server/main.py` now query the in-memory cache instead of making live API calls.
- The server dynamically discovers and watches claim types based on the installed XRDs.

## Project Structure

- `src/server/` — Contains the MCP server implementation (`main.py`) and caching logic (`cache.py`).
- `src/client/` — Contains a sample MCP client (`client.py`) that demonstrates how to send requests with context to the server.

## Prerequisites

- Python >= 3.13
- [uv](https://github.com/astral-sh/uv)
- A running Kubernetes cluster with Crossplane installed.

## Usage

### Running the MCP Server

You can run the server directly using [uv](https://github.com/astral-sh/uv):

```bash
uv run python src/server/main.py
```

The server will be available at `http://127.0.0.1:8000`.

Or, if you want to use the sample client:

```bash
uv run python src/client/client.py
```

### Example: Integrating with VSCode or Claude Desktop

In `vscode`, add the following to `mcp.json` under your workspace folder:
```json
{
  "inputs": [],
  "servers": {
    "CrossplaneServer": {
      "type": "sse",
      "url": "http://127.0.0.1:8000/mcp"
    }
  }
}
```

In `Claude Desktop`, add the following to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "crossplane-mcp-server": {
      "type": "sse",
      "url": "http://127.0.0.1:8000/mcp"
    }
  }
}
```

## Running Tests

To run all tests, use the following command:

```bash
uv run python -m unittest discover src
```

## Linting and Formatting

This project uses `ruff` for linting and formatting. You can run the linter and formatter using the following commands:

```bash
uv run ruff check .
uv run ruff format .
```

## Supported Tools

- [x] List Compositions
- [x] Get Composition
- [x] List CompositeResourceDefinitions (XRDs)
- [x] Get CompositeResourceDefinition (XRD)
- [x] List Claims
- [x] Find Managed Resources referenced by a CompositeResource
- [x] Diagnose Claim

## Development Status

- The server and client are separated for clarity and modularity.
- The client demonstrates real communication with the server using stdio.
- Context passing is supported and demonstrated in the client.
- The server now uses a caching layer for improved performance.

## Contributing

Contributions are welcome! Please open issues or pull requests for improvements or bug fixes.
