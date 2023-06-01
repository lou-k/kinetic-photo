import argparse
import json
import logging
import traceback
from http.client import HTTPException
from typing import List

from dependency_injector.wiring import Provide, inject
from flask import Flask, Response, jsonify, request
from kinetic_server.common import Content, Frame

from kinetic_server.content import ContentApi
from kinetic_server.frames import FramesApi

from .containers import Container

from dataclasses_json import dataclass_json
from dataclasses import dataclass

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

def create_server(environ=None, start_response=None):
    container = Container()
    app = Flask(__name__)
    app.container = container
    app.container.init_resources()
    app.container.wire(modules=[__name__])
    app.add_url_rule("/frame/<id>", "frame", frame)

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
