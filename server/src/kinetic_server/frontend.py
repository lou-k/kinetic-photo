from typing import Annotated
from fastapi import Depends, FastAPI

from .containers import Container
from .frames import FramesApi
from .db import ContentDb
from dependency_injector.wiring import Provide, inject

# Import UI components from centralized module
from .ui import Gallery, MainLayout


@inject
def init(
    fastapi_app: FastAPI, 
    frames_api: Annotated[FramesApi, Depends(Provide[Container.frames_api])],
    content_db: Annotated[ContentDb, Depends(Provide[Container.content_db])]
) -> None:
    """Initialize the frontend UI components"""
    
    # Create UI components
    gallery = Gallery(content_db)
    
    # Create and setup main layout
    layout = MainLayout(fastapi_app, frames_api, gallery)
    layout.setup()