# crossplane-mcp-server

A Python implementation of the Model Context Protocol (MCP) for Crossplane. This project enables LLMs and other clients to interact with Kubernetes and Crossplane resources (such as XRDs, Compositions, Claims, and Managed Resources) via a standardized protocol.

## Project Structure

- `src/server/` — Contains the MCP server implementation (see `server.py`).
- `src/client/` — Contains a sample MCP client (`client.py`) that demonstrates how to send requests with context to the server.

## Usage

### Running the MCP Server

You can run the server directly using [uv](https://github.com/astral-sh/uv):

```bash
uv run src/server/server.py
```

Or, if you want to use the sample client:

```bash
uv run src/client/client.py
```

### Example: Integrating with VSCode or Claude Desktop

In `vscode`, add the following to `mcp.json` under your workspace folder:
```json
{
  "inputs": [],
  "servers": {
    "CrossplaneServer": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "run",
        "src/server/server.py"
      ]
    }
  }
}
```

In `Claude Desktop`, add the following to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "crossplane-mcp-server": {
      "command": "uv",
      "args": [
        "run",
        "src/server/server.py"
      ]
    }
  }
}
```

## Supported Tools

- [x] List Compositions
- [x] Get Composition
- [x] List CompositeResourceDefinitions (XRDs)
- [x] Get CompositeResourceDefinition (XRD)
- [x] List Claims
- [x] Find Managed Resources referenced by a CompositeResource

## Development Status

- The server and client are separated for clarity and modularity.
- The client demonstrates real communication with the server using stdio.
- Context passing is supported and demonstrated in the client.

## Contributing

Contributions are welcome! Please open issues or pull requests for improvements or bug fixes.
