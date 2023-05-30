import inspect
import json
import logging
import sys
import urllib.request
from typing import Optional

from common import StreamMedia


class Processor:
    def __rep__(self):
        return json.dumps({"type": self.__class__.__name__, "params": self.__dict__})

    def __call__(self, media: StreamMedia) -> Optional[bytes]:
        """
        Processes the provided stream media into a video file.
        """
        ...

    @property
    def name(self) -> str:
        """
        Returns the processor name. This may change if we have hot-loadable processors or processors with different arguments.
        """
        return self.__class__.__name__


class CopyVideos(Processor):
    def __init__(self, **kwargs):
        pass

    def __call__(self, media: StreamMedia) -> Optional[bytes]:
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
    return r.__rep__()


def processor_converter(s: str) -> Processor:
    d = json.loads(s)
    return eval(d["type"])(**(d["params"]))


def list_processors() -> dict:
    return {
        name : obj
        for name, obj in inspect.getmembers(sys.modules[__name__], inspect.isclass)
        if issubclass(obj, Processor) and name != "Processor"
    }
