
import inspect
import sys

from .copy_video import CopyVideo
from .fade import Fade
from .filter import Filter
from .filter_seen import FilterSeen
from .depth import ComputeDepth
from .mesh import ComputeMesh
from .step import *


def list_steps() -> dict:
    """Enumerates the Steps available. The superclass is not included.

    Returns:
        dict: A dictionary of Step class name -> class object
    """
    return {
        name: obj
        for name, obj in inspect.getmembers(sys.modules[__name__], inspect.isclass)
        if issubclass(obj, Step) and name not in set(["Step", "ContentCreator", "ContentAugmentor"])
    }


def step_adapter(r: Step) -> str:
    """sqlite3 adapter for Step classes.

    Args:
        r (Step): The Step to serialize

    Returns:
        str: A serialized version of Step r
    """
    return r.__rep__()


def step_converter(s: str) -> Step:
    """sqlite3 converter for Step types.

    Args:
        s (str): A serialized version of a Step.

    Returns:
        Step: A de-serialized Step.
    """
    d = json.loads(s)
    return eval(d["type"])(**(d["params"]))
