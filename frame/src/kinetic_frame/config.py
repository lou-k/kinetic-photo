import os
from typing import Optional

import yaml
import logging

DEFAULT_CONFIG_PATH="/etc/kinetic-photo/frame/config.yml"

def _load(path: Optional[str]) -> dict:
    """Loads the frame's configuration.
    The following locations are tried (in this order):
    * The provided path
    * A path set in the KINETIC_FRAME_CONFIG environment variable
    * The default location DEFAULT_CONFIG_PATH

    Args:
        path (Optional[str]): Load the configuration from this file

    Returns:
        dict: A dictionary contianing this frame's configuration.
    """
    if path:
        file_to_load = path
    else:
        file_to_load = os.environ.get("KINETIC_FRAME_CONFIG", DEFAULT_CONFIG_PATH)
    
    with open(file_to_load) as file:
        return yaml.safe_load(file)
