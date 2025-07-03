
import unittest
from unittest.mock import patch, MagicMock
from server.main import diagnose_claim

class TestDiagnoseClaim(unittest.IsolatedAsyncioTestCase):

    @patch('server.main.cache.get_cache')
    @patch('server.main.k8s_client')
    async def test_diagnose_claim_happy_path(self, mock_k8s_client, mock_get_cache):
        # Mock Cache
        mock_get_cache.return_value = {
            "compositeresourcedefinitions": {
                "xrd1": {
                    "metadata": {"name": "xrd1"},
                    "spec": {
                        "group": "example.com",
                        "names": {"plural": "compositeresources", "kind": "CompositeResource"},
                        "claimNames": {"plural": "claims", "kind": "Claim"},
                        "versions": [{"name": "v1alpha1"}]
                    }
                }
            },
            "claims/claims": {
                "default/test-claim": {
                    "metadata": {"name": "test-claim", "namespace": "default"},
                    "kind": "Claim",
                    "spec": {"resourceRef": {"apiVersion": "example.com/v1alpha1", "kind": "CompositeResource", "name": "test-xr"}},
                    "status": {"conditions": [{"type": "Ready", "status": "True"}]}
                }
            }
        }

        # Mock Live K8s calls (for XR and MR)
        mock_xr = {
            "metadata": {"name": "test-xr"},
            "kind": "CompositeResource",
            "status": {
                "conditions": [{"type": "Ready", "status": "True"}],
                "resourceRefs": [
                    {"apiVersion": "test.group/v1", "kind": "ManagedResource", "name": "test-mr"}
                ]
            }
        }
        mock_mr = {
            "metadata": {"name": "test-mr"},
            "kind": "ManagedResource",
            "status": {"conditions": [{"type": "Ready", "status": "True"}]}
        }
        mock_k8s_client.get_cluster_custom_object.return_value = mock_xr
        mock_k8s_client.get_namespaced_custom_object.return_value = mock_mr

        context = {}
        result = await diagnose_claim(context, "test-claim", "default", "Claim")

        self.assertTrue(result["success"])
        self.assertIn("All resources (Claim, XR, and MRs) are reporting a Ready status.", result["diagnosis"]["summary"])

    @patch('server.main.cache.get_cache')
    @patch('server.main.k8s_client')
    async def test_diagnose_claim_unhappy_path(self, mock_k8s_client, mock_get_cache):
        mock_get_cache.return_value = {
            "compositeresourcedefinitions": {
                "xrd1": {
                    "metadata": {"name": "xrd1"},
                    "spec": {
                        "group": "example.com",
                        "names": {"plural": "compositeresources", "kind": "CompositeResource"},
                        "claimNames": {"plural": "claims", "kind": "Claim"},
                        "versions": [{"name": "v1alpha1"}]
                    }
                }
            },
            "claims/claims": {
                "default/test-claim": {
                    "metadata": {"name": "test-claim", "namespace": "default"},
                    "kind": "Claim",
                    "spec": {"resourceRef": {"apiVersion": "example.com/v1alpha1", "kind": "CompositeResource", "name": "test-xr"}},
                    "status": {"conditions": [{"type": "Ready", "status": "False", "reason": "Unavailable", "message": "Claim is not ready"}]}
                }
            }
        }

        mock_xr = {
            "metadata": {"name": "test-xr"},
            "kind": "CompositeResource",
            "status": {
                "conditions": [{"type": "Ready", "status": "False", "reason": "Unavailable", "message": "XR is not ready"}],
                "resourceRefs": []
            }
        }
        mock_k8s_client.get_cluster_custom_object.return_value = mock_xr

        context = {}
        result = await diagnose_claim(context, "test-claim", "default", "Claim")

        self.assertTrue(result["success"])
        self.assertIn("Claim 'test-claim' is not ready. Reason: Unavailable. Message: Claim is not ready", result["diagnosis"]["summary"])
        self.assertIn("Composite Resource 'test-xr' is not ready. Reason: Unavailable. Message: XR is not ready", result["diagnosis"]["summary"])

    @patch('server.main.cache.get_cache')
    async def test_diagnose_claim_not_found(self, mock_get_cache):
        mock_get_cache.return_value = {
            "compositeresourcedefinitions": {
                "xrd1": {
                    "metadata": {"name": "xrd1"},
                    "spec": {
                        "group": "example.com",
                        "names": {"plural": "compositeresources", "kind": "CompositeResource"},
                        "claimNames": {"plural": "claims", "kind": "Claim"},
                        "versions": [{"name": "v1alpha1"}]
                    }
                }
            },
            "claims/claims": {}
        }

        context = {}
        result = await diagnose_claim(context, "non-existent-claim", "default", "Claim")

        self.assertFalse(result["success"])
        self.assertIn("Claim 'non-existent-claim' of kind 'Claim' not found in namespace 'default'", result["error"])

if __name__ == '__main__':
    unittest.main()
