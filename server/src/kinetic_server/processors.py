import inspect
import json
import logging
import sys
import urllib.request
from typing import Optional

from .common import StreamMedia


class Processor:
    """A processor converts stream media (i.e., source images or videos) into kinetic photos.

    Each processor may have different input requirements or parameters, so they could reject photos
    based on their content, type, etc.
    """
    def __rep__(self) -> str:
        """Serialized this processor into a string.

        Returns:
            str: A json encoded dictionary containing this processors classname and parameters.
        """

        return json.dumps({"type": self.__class__.__name__, "params": self.__dict__})

    def __call__(self, media: StreamMedia) -> Optional[bytes]:
        """Processes the provided media into a kinetic photo if possible, and returns the resulting video clip.

        Args:
            media (StreamMedia): The media to generate a kinetic photo from.

        Returns:
            Optional[bytes]: None if the media could not be processed, or a compressed video file if successful.
        """
        ...

    @property
    def name(self) -> str:
        """Returns the processor name. This may change if we have hot-loadable processors or processors with different arguments.


        Returns:
            str: The name of this processor
        """
        return self.__class__.__name__


class CopyVideos(Processor):
    """A simple processor that just downloads video clips.

    Args:
        Processor (Processor): Superclass
    """
    def __init__(self, **kwargs):
        pass

    def __call__(self, media: StreamMedia) -> Optional[bytes]:
        """Downloads the provided video clip if present.

        Args:
            media (StreamMedia): The stream media (hoppefully) containing a video.

        Returns:
            Optional[bytes]: The video bytes or None if stream media is an image.
        """
        if media.is_video:
            if media.url:
                logging.info(f"Downloading {media.url}....")
                response = urllib.request.urlopen(media.url)
                return response.read()
            else:
                logging.info(
                    f"Media {media.external_id} does not have a url to download.."
                )
        else:
            logging.info(
                f"Skipping media {media.filename} from stream {media.stream_id} since it is not a video."
            )


def processor_adapter(r: Processor) -> str:
    """sqlite3 adapter for Processor classes.

    Args:
        r (Processor): The processor to serialize

    Returns:
        str: A serialized version of processor r
    """
    return r.__rep__()


def processor_converter(s: str) -> Processor:
    """sqlite3 converter for processor types.

    Args:
        s (str): A serialized version of a processor.

    Returns:
        Processor: A de-serialized processor.
    """
    d = json.loads(s)
    return eval(d["type"])(**(d["params"]))


def list_processors() -> dict:
    """Enumerates the processors available. The superclass is not included.

    Returns:
        dict: A dictionary of processor class name -> class object
    """
    return {
        name : obj
        for name, obj in inspect.getmembers(sys.modules[__name__], inspect.isclass)
        if issubclass(obj, Processor) and name != "Processor"
    }
