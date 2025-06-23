import unittest
from unittest.mock import patch, MagicMock
import src.client.client as client_mod

class TestMCPClient(unittest.TestCase):
    @patch('subprocess.Popen')
    def test_send_request_success(self, mock_popen):
        # Mock the server process
        mock_proc = MagicMock()
        mock_proc.stdin.write = MagicMock()
        mock_proc.stdin.flush = MagicMock()
        mock_proc.stdout.readline.return_value = '{"result": "ok"}\n'
        mock_proc.stderr.read.return_value = ''
        mock_proc.terminate = MagicMock()
        mock_popen.return_value = mock_proc

        response = client_mod.send_request("list_compositions", {}, {"user": "alice", "namespace": "dev"})
        self.assertIn("result", response)
        self.assertEqual(response["result"], "ok")

    @patch('subprocess.Popen')
    def test_send_request_invalid_json(self, mock_popen):
        mock_proc = MagicMock()
        mock_proc.stdin.write = MagicMock()
        mock_proc.stdin.flush = MagicMock()
        mock_proc.stdout.readline.return_value = 'not a json\n'
        mock_proc.stderr.read.return_value = ''
        mock_proc.terminate = MagicMock()
        mock_popen.return_value = mock_proc

        response = client_mod.send_request("list_compositions", {}, {"user": "bob"})
        self.assertIn("error", response)
        self.assertIn("Invalid response", response["error"])

if __name__ == "__main__":
    unittest.main()

