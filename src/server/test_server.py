import unittest
from unittest.mock import patch, MagicMock

# Import the server module
import src.server.server as server_mod

class TestMCPServer(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Patch Kubernetes client
        self.k8s_patch = patch('src.server.server.init_kubernetes_client')
        self.mock_k8s = self.k8s_patch.start()
        self.mock_client = MagicMock()
        self.mock_k8s.return_value = self.mock_client

    def tearDown(self):
        self.k8s_patch.stop()

    async def test_list_compositions(self):
        self.mock_client.list_cluster_custom_object.return_value = {"items": ["comp1", "comp2"]}
        context = {"namespace": None}
        result = await server_mod.list_compositions(context)
        self.assertTrue(result["success"])
        self.assertEqual(result["count"], 2)

    async def test_get_composition_found(self):
        self.mock_client.get_cluster_custom_object.return_value = {"name": "comp1"}
        context = {"namespace": None}
        result = await server_mod.get_composition(context, "comp1")
        self.assertTrue(result["success"])
        self.assertEqual(result["composition"]["name"], "comp1")

    async def test_get_composition_not_found(self):
        from kubernetes.client.rest import ApiException
        self.mock_client.get_cluster_custom_object.side_effect = ApiException(status=404)
        context = {"namespace": None}
        result = await server_mod.get_composition(context, "notfound")
        self.assertFalse(result["success"])
        self.assertIn("not found", result["error"])

if __name__ == "__main__":
    unittest.main()

