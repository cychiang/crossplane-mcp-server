
import unittest
from unittest.mock import patch, MagicMock
from src.server.server import diagnose_claim
from kubernetes.client.rest import ApiException

class TestDiagnoseClaim(unittest.IsolatedAsyncioTestCase):

    @patch('src.server.server.init_kubernetes_client')
    async def test_diagnose_claim_happy_path(self, mock_init_k8s_client):
        mock_k8s_client = MagicMock()
        mock_init_k8s_client.return_value = mock_k8s_client

        # Mock XRDs
        mock_xrds = {
            "items": [
                {
                    "spec": {
                        "group": "example.com",
                        "names": {"plural": "compositeresources", "kind": "CompositeResource"},
                        "claimNames": {"plural": "claims", "kind": "Claim"},
                        "versions": [{"name": "v1alpha1"}]
                    }
                }
            ]
        }
        # Mock Claim
        mock_claim = {
            "metadata": {"name": "test-claim", "namespace": "default"},
            "kind": "Claim",
            "spec": {"resourceRef": {"apiVersion": "example.com/v1alpha1", "kind": "CompositeResource", "name": "test-xr"}},
            "status": {"conditions": [{"type": "Ready", "status": "True", "reason": "Available", "message": "Claim is ready"}]}
        }
        # Mock Composite Resource (XR)
        mock_xr = {
            "metadata": {"name": "test-xr"},
            "kind": "CompositeResource",
            "status": {
                "conditions": [{"type": "Ready", "status": "True", "reason": "Available", "message": "XR is ready"}],
                "resourceRefs": [
                    {"apiVersion": "test.group/v1", "kind": "ManagedResource", "name": "test-mr"}
                ]
            }
        }
        # Mock Managed Resource (MR)
        mock_mr = {
            "metadata": {"name": "test-mr"},
            "kind": "ManagedResource",
            "status": {"conditions": [{"type": "Ready", "status": "True", "reason": "Available", "message": "MR is ready"}]}
        }

        mock_k8s_client.list_cluster_custom_object.return_value = mock_xrds
        mock_k8s_client.get_namespaced_custom_object.side_effect = [
            mock_claim,  # First call for the claim
            mock_mr      # Second call for the managed resource
        ]
        mock_k8s_client.get_cluster_custom_object.return_value = mock_xr

        context = {}
        result = await diagnose_claim(context, "test-claim", "default", "Claim")

        self.assertTrue(result["success"])
        self.assertIn("All resources (Claim, XR, and MRs) are reporting a Ready status.", result["diagnosis"]["summary"])

    @patch('src.server.server.init_kubernetes_client')
    async def test_diagnose_claim_unhappy_path(self, mock_init_k8s_client):
        mock_k8s_client = MagicMock()
        mock_init_k8s_client.return_value = mock_k8s_client

        # Mock XRDs
        mock_xrds = {
            "items": [
                {
                    "spec": {
                        "group": "example.com",
                        "names": {"plural": "compositeresources", "kind": "CompositeResource"},
                        "claimNames": {"plural": "claims", "kind": "Claim"},
                        "versions": [{"name": "v1alpha1"}]
                    }
                }
            ]
        }
        # Mock Claim
        mock_claim = {
            "metadata": {"name": "test-claim", "namespace": "default"},
            "kind": "Claim",
            "spec": {"resourceRef": {"apiVersion": "example.com/v1alpha1", "kind": "CompositeResource", "name": "test-xr"}},
            "status": {"conditions": [{"type": "Ready", "status": "False", "reason": "Unavailable", "message": "Claim is not ready"}]}
        }
        # Mock Composite Resource (XR)
        mock_xr = {
            "metadata": {"name": "test-xr"},
            "kind": "CompositeResource",
            "status": {
                "conditions": [{"type": "Ready", "status": "False", "reason": "Unavailable", "message": "XR is not ready"}],
                "resourceRefs": [
                    {"apiVersion": "test.group/v1", "kind": "ManagedResource", "name": "test-mr"}
                ]
            }
        }
        # Mock Managed Resource (MR)
        mock_mr = {
            "metadata": {"name": "test-mr"},
            "kind": "ManagedResource",
            "status": {"conditions": [{"type": "Ready", "status": "False", "reason": "Unavailable", "message": "MR is not ready"}]}
        }

        mock_k8s_client.list_cluster_custom_object.return_value = mock_xrds
        mock_k8s_client.get_namespaced_custom_object.side_effect = [
            mock_claim,
            mock_mr
        ]
        mock_k8s_client.get_cluster_custom_object.return_value = mock_xr

        context = {}
        result = await diagnose_claim(context, "test-claim", "default", "Claim")

        self.assertTrue(result["success"])
        self.assertIn("Claim 'test-claim' is not ready. Reason: Unavailable. Message: Claim is not ready", result["diagnosis"]["summary"])
        self.assertIn("Composite Resource 'test-xr' is not ready. Reason: Unavailable. Message: XR is not ready", result["diagnosis"]["summary"])
        self.assertIn("Composite Resource 'test-xr' is not ready. Reason: Unavailable. Message: XR is not ready", result["diagnosis"]["summary"])

    @patch('src.server.server.init_kubernetes_client')
    async def test_diagnose_claim_not_found(self, mock_init_k8s_client):
        mock_k8s_client = MagicMock()
        mock_init_k8s_client.return_value = mock_k8s_client

        mock_xrds = {
            "items": [
                {
                    "spec": {
                        "group": "example.com",
                        "names": {"plural": "compositeresources", "kind": "CompositeResource"},
                        "claimNames": {"plural": "claims", "kind": "Claim"},
                        "versions": [{"name": "v1alpha1"}]
                    }
                }
            ]
        }

        mock_k8s_client.list_cluster_custom_object.return_value = mock_xrds
        mock_k8s_client.get_namespaced_custom_object.side_effect = ApiException(status=404)

        context = {}
        result = await diagnose_claim(context, "non-existent-claim", "default", "Claim")

        self.assertFalse(result["success"])
        self.assertIn("Claim 'non-existent-claim' of kind 'Claim' not found in namespace 'default'", result["error"])

if __name__ == '__main__':
    unittest.main()
