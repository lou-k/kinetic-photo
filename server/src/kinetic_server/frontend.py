from typing import Annotated
from fastapi import Depends, FastAPI

from .containers import Container
from .frames import FramesApi
from .db import ContentDb
from .streams import StreamsApi
from .pipelines import PipelineApi
from dependency_injector.wiring import Provide, inject

# Import UI components from centralized module
from .ui import MainLayout

@inject
def init(
    fastapi_app: FastAPI, 
    frames_api: Annotated[FramesApi, Depends(Provide[Container.frames_api])],
    content_db: Annotated[ContentDb, Depends(Provide[Container.content_db])],
    streams_api: Annotated[StreamsApi, Depends(Provide[Container.streams_api])],
    pipeline_api: Annotated[PipelineApi, Depends(Provide[Container.pipeline_api])]
) -> None:
    """Initialize the frontend UI components"""
    
    # Create and setup main layout
    layout = MainLayout(fastapi_app, frames_api, content_db, streams_api, pipeline_api)
