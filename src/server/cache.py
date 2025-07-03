
import logging
import threading
from typing import Dict, Any, List, Callable, Optional

from kubernetes import client, config, watch

# Set up logging
logger = logging.getLogger(__name__)

# Type Aliases
K8sObject = Dict[str, Any]
ResourceCache = Dict[str, K8sObject]
Cache = Dict[str, ResourceCache]

# Global cache and lock
_cache: Cache = {
    "compositions": {},
    "compositeresourcedefinitions": {},
    "claims": {},
}
_cache_lock = threading.Lock()
_watch_threads: List[threading.Thread] = []
_stop_event = threading.Event()


def get_cache() -> Cache:
    """Returns a thread-safe copy of the cache."""
    with _cache_lock:
        return _cache.copy()


def _get_resource_key(resource: K8sObject) -> str:
    """Generate a unique key for a Kubernetes resource."""
    namespace = resource.get("metadata", {}).get("namespace")
    name = resource.get("metadata", {}).get("name")
    return f"{namespace}/{name}" if namespace else name


def _watch_resource_type(
    plural_name: str,
    list_func: Callable[..., Dict[str, Any]],
    *args,
    **kwargs,
):
    """
    Watches a specific Kubernetes resource type and updates the cache.
    This function is designed to be run in a background thread.
    """
    w = watch.Watch()
    logger.info(f"Starting watch for resource type: {plural_name}")
    try:
        stream = w.stream(list_func, *args, **kwargs)
        for event in stream:
            if _stop_event.is_set():
                break
            obj = event["object"]
            key = _get_resource_key(obj)
            with _cache_lock:
                cache_for_type = _cache.setdefault(plural_name, {})
                if event["type"] == "ADDED" or event["type"] == "MODIFIED":
                    cache_for_type[key] = obj
                elif event["type"] == "DELETED":
                    cache_for_type.pop(key, None)
    except Exception as e:
        logger.error(f"Error watching {plural_name}: {e}", exc_info=True)
    finally:
        w.stop()
        logger.info(f"Stopped watch for resource type: {plural_name}")


def start_watching(k8s_client: client.CustomObjectsApi):
    """
    Starts watching Crossplane resources in background threads.
    """
    global _watch_threads
    if _watch_threads:
        logger.warning("Watch threads already started.")
        return

    watch_definitions = [
        {
            "plural_name": "compositions",
            "list_func": k8s_client.list_cluster_custom_object,
            "args": {
                "group": "apiextensions.crossplane.io",
                "version": "v1",
                "plural": "compositions",
            },
        },
        {
            "plural_name": "compositeresourcedefinitions",
            "list_func": k8s_client.list_cluster_custom_object,
            "args": {
                "group": "apiextensions.crossplane.io",
                "version": "v1",
                "plural": "compositeresourcedefinitions",
            },
        },
    ]

    # To watch claims, we first need to get all XRDs and then start a watch for each claim type.
    try:
        xrd_list = k8s_client.list_cluster_custom_object(
            group="apiextensions.crossplane.io",
            version="v1",
            plural="compositeresourcedefinitions",
        )

        for xrd in xrd_list.get("items", []):
            if "claimNames" not in xrd.get("spec", {}):
                continue

            claim_plural = xrd["spec"]["claimNames"]["plural"]
            claim_group = xrd["spec"]["group"]
            claim_version = xrd["spec"]["versions"][0]["name"]

            claim_definition = {
                "plural_name": f"claims/{claim_plural}",
                "list_func": k8s_client.list_cluster_custom_object,
                "args": {
                    "group": claim_group,
                    "version": claim_version,
                    "plural": claim_plural,
                },
            }
            watch_definitions.append(claim_definition)

    except Exception as e:
        logger.error(f"Could not list XRDs to start claim watchers: {e}")

    for definition in watch_definitions:
        thread = threading.Thread(
            target=_watch_resource_type,
            args=(
                definition["plural_name"],
                definition["list_func"],
            ),
            kwargs=definition["args"],
            daemon=True,
        )
        thread.start()
        _watch_threads.append(thread)

    logger.info(f"Started {_watch_threads.__len__()} watch threads.")


def stop_watching():
    """
    Signals all watch threads to stop.
    """
    logger.info("Stopping all watch threads...")
    _stop_event.set()
    for thread in _watch_threads:
        thread.join(timeout=5)
