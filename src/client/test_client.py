import unittest
import threading
import uvicorn
import time
import requests

from src.server import main as server_mod
import src.client.client as client_mod

class TestMCPClientIntegration(unittest.TestCase):
    server_thread = None
    server_started = threading.Event()

    @classmethod
    def run_server(cls):
        app = server_mod.mcp.run(transport="sse")
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")

    @classmethod
    def setUpClass(cls):
        """Starts the MCP server in a background thread before any tests run."""
        cls.server_thread = threading.Thread(target=cls.run_server, daemon=True)
        cls.server_thread.start()
        # Wait for the server to start by polling the health check endpoint
        for _ in range(20):
            try:
                response = requests.get("http://127.0.0.1:8000/health")
                if response.status_code == 200:
                    return
            except requests.ConnectionError:
                pass
            time.sleep(1)
        raise RuntimeError("Server did not start in time")

    def test_send_request_lists_compositions(self):
        """Tests if the client can successfully get a response from the live server."""
        response = client_mod.send_request("list_compositions", {}, {"user": "test"})
        self.assertIn("result", response)
        self.assertTrue(response["result"]["success"])
        self.assertIn("compositions", response["result"])

if __name__ == "__main__":
    unittest.main()


