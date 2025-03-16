import argparse

import uvicorn
from fastapi import FastAPI

from . import endpoints
from .containers import Container


#
# Create FastAPI app
#
def create_server() -> FastAPI:
    container = Container()

    app = FastAPI(title="Kinetic Photo Server")
    app.container = container
    app.container.init_resources()
    app.container.wire(modules=[__name__, ".endpoints"])
    app.include_router(endpoints.router)

    return app


def parse_args(args=None):
    parser = argparse.ArgumentParser(description="The Kinetic Photo server application")
    parser.add_argument(
        "--port", type=int, default=8080, help="Port to run the server on."
    )
    parser.add_argument(
        "--host", type=str, default="0.0.0.0", help="Host to run the server on."
    )
    return parser.parse_args(args)


if __name__ == "__main__":
    # This main function is used for debugging only.
    # Uvicorn will be used to serve the application when deployed.

    args = parse_args()
    app = create_server()

    uvicorn.run(app, host=args.host, port=args.port)
