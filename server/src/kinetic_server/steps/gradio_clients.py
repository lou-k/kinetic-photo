import json
import logging
from gradio_client import Client

_client_cache = {}

def get(warmup: bool = False, **kwargs) -> Client:
    """Keeps gradio clients cached in memory so that steps don't need to maintain pointers to them.

    Returns:
        Client: The client loaded for the provided arguments
    """
    key = json.dumps(kwargs)
    if key not in _client_cache:
        _client_cache[key] = Client(**kwargs)
        if warmup:
            logging.info(f"Sending bogus data to warm up {key}")
            try:
                _client_cache[key].predict("http://www.google.com", api_name="/predict")
            except Exception as e:
                pass
    return _client_cache[key]
