# crossplane-mcp-server - WIP

A Python server that implements Model Context Protocol(MCP) for Crossplane. It allows LLM to talk to Kubernetes and query Crossplane-related resources, such as, CompositeResourceDefinition(XRD), Composition, and ManagedResource(MR).

## Usage

Using Crossplane MCP Server in `vscode`, add the following to `mcp.json` under workspace folder.
```json
{
  "inputs": [],
  "servers": {
    "CrossplaneServer": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "--directory",
        "${PATH_TO_CROSSPLANE_MCP_SERVER}/crossplane-mcp-server",
        "run",
        "src/server.py"
      ]
    }
  }
}
```

Using Crossplane MCP Server in `Claude Desktop`, add the following to `claude_desktop_config.json`.
```json
{
  "mcpServers": {
    "crossplane-mcp-server": {
      "command": "uv",
      "args": [
        "--directory",
        "${PATH_TO_CROSSPLANE_MCP_SERVER}/crossplane-mcp-server",
        "run",
        "src/server.py"
      ]
    }
  }
}
```

## Support tools

[ ] List Compositions
[ ] Get Composition
[ ] List CompositeResourceDefinitions
[ ] Get CompositeResourceDefinition
[ ] ...TBC
