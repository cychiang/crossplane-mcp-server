import unittest
from unittest.mock import patch

import src.server.main as server_mod

class TestMCPServer(unittest.IsolatedAsyncioTestCase):

    @patch('src.server.cache.get_cache')
    async def test_list_compositions(self, mock_get_cache):
        mock_get_cache.return_value = {
            "compositions": {
                "comp1": {"metadata": {"name": "comp1"}},
                "comp2": {"metadata": {"name": "comp2"}},
            }
        }
        context = {"namespace": None}
        result = await server_mod.list_compositions(context)
        self.assertTrue(result["success"])
        self.assertEqual(result["count"], 2)

    @patch('src.server.cache.get_cache')
    async def test_get_composition_found(self, mock_get_cache):
        mock_get_cache.return_value = {
            "compositions": {
                "comp1": {"metadata": {"name": "comp1"}},
            }
        }
        context = {"namespace": None}
        result = await server_mod.get_composition(context, "comp1")
        self.assertTrue(result["success"])
        self.assertEqual(result["composition"]["metadata"]["name"], "comp1")

    @patch('src.server.cache.get_cache')
    async def test_get_composition_not_found(self, mock_get_cache):
        mock_get_cache.return_value = {
            "compositions": {}
        }
        context = {"namespace": None}
        result = await server_mod.get_composition(context, "notfound")
        self.assertFalse(result["success"])
        self.assertIn("not found", result["error"])

if __name__ == "__main__":
    unittest.main()

