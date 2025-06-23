import subprocess
import sys
import json
from typing import Dict, Any
import os


def send_request(method: str, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send a request to the MCP server via stdio subprocess.
    """
    request = {
        "method": method,
        "params": params,
        "context": context,
        "id": 1
    }
    # Find the server.py path
    server_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "server", "server.py")
    # Start the server as a subprocess
    proc = subprocess.Popen(
        [sys.executable, server_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    # Send the request
    proc.stdin.write(json.dumps(request) + "\n")
    proc.stdin.flush()
    # Read the response
    response_line = proc.stdout.readline()
    try:
        response = json.loads(response_line)
    except Exception:
        response = {"error": "Invalid response from server", "raw": response_line}
    # Optionally, print server stderr for debugging
    err = proc.stderr.read()
    if err:
        print("[Server stderr]", err)
    proc.terminate()
    return response

if __name__ == "__main__":
    # Example usage: list compositions in the 'dev' namespace as user 'alice'
    context = {
        "user": "alice",
        "namespace": "dev"
    }
    response = send_request("list_compositions", {}, context)
    print("Server response:", response)
