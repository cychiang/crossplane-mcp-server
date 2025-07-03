import unittest
from unittest.mock import MagicMock, patch
import threading
import time

from src.server import cache

class TestCache(unittest.TestCase):

    def setUp(self):
        # Reset the cache and stop event before each test
        cache._cache = {
            "compositions": {},
            "compositeresourcedefinitions": {},
            "claims": {},
        }
        cache._stop_event.clear()
        cache._watch_threads.clear()

    def test_get_resource_key(self):
        resource_with_namespace = {"metadata": {"name": "test", "namespace": "default"}}
        self.assertEqual(cache._get_resource_key(resource_with_namespace), "default/test")

        resource_without_namespace = {"metadata": {"name": "test"}}
        self.assertEqual(cache._get_resource_key(resource_without_namespace), "test")

    @patch('src.server.cache.watch.Watch')
    def test_watch_resource_type(self, mock_watch):
        mock_stream = [
            {"type": "ADDED", "object": {"metadata": {"name": "comp1", "namespace": "default"}}},
            {"type": "MODIFIED", "object": {"metadata": {"name": "comp2"}}},
            {"type": "DELETED", "object": {"metadata": {"name": "comp1", "namespace": "default"}}},
        ]
        stream_processed = threading.Event()

        def stream_side_effect(*args, **kwargs):
            yield from mock_stream
            stream_processed.set()

        mock_watch.return_value.stream.return_value = stream_side_effect()

        list_func = MagicMock()
        watcher_thread = threading.Thread(target=cache._watch_resource_type, args=("compositions", list_func))
        watcher_thread.start()

        processed = stream_processed.wait(timeout=1)
        self.assertTrue(processed, "Watcher did not process the stream in time")

        cache._stop_event.set()
        watcher_thread.join(timeout=1)
        self.assertFalse(watcher_thread.is_alive(), "Watcher thread did not stop")

        cached_data = cache.get_cache()["compositions"]
        self.assertIn("comp2", cached_data)
        self.assertNotIn("default/comp1", cached_data)

    @patch('src.server.cache._watch_resource_type')
    def test_start_watching(self, mock_watch_resource_type):
        can_stop = threading.Event()

        def mock_side_effect(*args, **kwargs):
            can_stop.wait()

        mock_watch_resource_type.side_effect = mock_side_effect

        mock_k8s_client = MagicMock()
        cache.start_watching(mock_k8s_client)

        self.assertEqual(len(cache._watch_threads), 2)
        time.sleep(0.1) # Give threads time to start
        self.assertTrue(all(t.is_alive() for t in cache._watch_threads))

        can_stop.set()
        cache.stop_watching()

        for t in cache._watch_threads:
            t.join(timeout=1)

        self.assertTrue(all(not t.is_alive() for t in cache._watch_threads))

if __name__ == '__main__':
    unittest.main()