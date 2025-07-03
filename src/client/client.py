import requests
import json
from typing import Dict, Any

def send_request(method: str, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send a request to the MCP server via HTTP SSE.
    """
    request = {
        "method": method,
        "params": params,
        "context": context,
        "id": 1
    }
    try:
        response = requests.post(
            "http://127.0.0.1:8000/mcp",
            json=request,
            stream=True,  # SSE is a streaming protocol
            timeout=10
        )
        response.raise_for_status()  # Raise an exception for bad status codes

        # For SSE, we get a stream of events. For a simple request/response, we expect one event.
        for line in response.iter_lines():
            if line.startswith(b'data:'):
                try:
                    return json.loads(line[5:])
                except json.JSONDecodeError:
                    return {"error": "Invalid JSON in SSE response", "raw": line[5:].decode()}
        return {"error": "No data received in SSE response"}

    except requests.exceptions.RequestException as e:
        return {"error": f"HTTP request failed: {e}"}


if __name__ == "__main__":
    # Example usage: list compositions in the 'dev' namespace as user 'alice'
    context = {
        "user": "alice",
        "namespace": "dev"
    }
    response = send_request("list_compositions", {}, context)
    print("Server response:", response)
