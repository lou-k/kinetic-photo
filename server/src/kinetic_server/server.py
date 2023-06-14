import argparse
import sys
from dataclasses import dataclass
from typing import List

from dataclasses_json import dataclass_json
from dependency_injector.wiring import Provide, inject
from disk_objectstore import Container as DiskContainer
from flask import Flask, request

from .common import Content, Frame, initialize_objectstore
from .containers import Container
from .frames import FramesApi


#
# API types
#
@dataclass_json
@dataclass
class GetFrameResult:
    frame: Frame
    content: List[Content]


#
# Endpoints
#


@inject
def frame(
    id: str,
    frames_api: FramesApi = Provide[Container.frames_api],
):
    frame = frames_api.get(id)
    content = frames_api.get_content_for(id)
    resp = GetFrameResult(frame=frame, content=content)
    return resp.to_dict()


@inject
def playlist(id: str, frames_api: FramesApi = Provide[Container.frames_api]):
    if id == "all":
        version="faded"
        content = frames_api._content_db.query(sys.maxsize)
    else:
        frame = frames_api.get(id)
        version = frame.options.get("preffered_version", "original")
        content = frames_api.get_content_for(id)
    res = "#EXTM3U\n"
    for c in content:
        id = c.versions.get(version, c.id)
        duration = str(int(c.metadata['duration'])) if c.metadata and 'duration' in c.metadata else ""
        res += f"#EXINF:{duration}\n{request.url_root}video/{id}\n"
    res += "#EXT-X-ENDLIST"
    return res, 200, {"Content-Type": "video/mp4"}


@inject
def video(id: str, object_store: DiskContainer = Provide[Container.object_store]):
    if object_store.has_object(id):
        video_object = object_store.get_object_content(id)
        # TODO -- ensure that the content type is correct - maybe store it in the objectstore?
        return video_object, 200, {"Content-Type": "video/mp4"}
    else:
        return {}, 404


def create_server():
    container = Container()
    app = Flask(__name__)
    app.container = container
    app.container.init_resources()
    app.container.wire(modules=[__name__])
    initialize_objectstore(container.object_store.provided())
    app.add_url_rule("/frame/<id>", "frame", frame)
    app.add_url_rule("/video/<id>", "video", video)
    app.add_url_rule("/playlist/<id>.m3u8", "playlist", playlist)

    return app


def parse_args(args=None):
    parser = argparse.ArgumentParser(description="The Kinetic Photo server application")
    parser.add_argument(
        "--port", type=int, default=8080, help="Port to run the server on."
    )
    parser.add_argument(
        "--host", type=str, default="0.0.0.0", help="Host to run the server on."
    )
    parser.add_argument("--debug", action=argparse.BooleanOptionalAction)
    return parser.parse_args(args)


if __name__ == "__main__":
    # This main function is used for debugging only.
    # Waitress will be used to serve the application when deployed.

    args = parse_args()
    app = create_server()

    app.run(host=args.host, port=args.port, debug=args.debug)
