# crossplane-mcp-server

In this project, it's trying to implement a Crossplane MCP server that can be used to query and find Crossplane resources.

Based on the context from users, it will switch to different kubernetes cluster and query the Crossplane resources from there.

# requirements

- package management system: `uv`
- python version: `3.13+`

# crossplane-mcp-server requirements

- subprojects for `server` and `client`
- In the client, it implements a sample MCP client that can send requests with context to the server we built.
- In the server, it implements the MCP server that can handle requests and responses based on the model context protocol (MCP).
- The server and client should be implemented on top of the `mcp` library and latest one.
- The project is already implemented with some features, you can review those features and see if them work.

## Functionality

- User can give a context of the kubernetes cluster along with claim name and namespace. The MCP server should be able to address
  the underline CompositeResources and ManagedResources based on the context provided.
- User can give a context like what claims are not healthy which means either `Synced` or `Ready` is not `True`. 
  Remember that claim is a namespaced resource so you might need to traverse the namespaces to find the claims that are not healthy.
