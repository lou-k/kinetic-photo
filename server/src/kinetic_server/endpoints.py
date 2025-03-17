import sys
from dataclasses import dataclass
from typing import Annotated, List, Optional

from dataclasses_json import dataclass_json
from dependency_injector.wiring import Provide, inject
from fastapi import Request, Response, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

from .common import Content, Frame
from .containers import Container
from .db import ContentDb, PreRenderDb
from .frames import FramesApi
from .object_store import ObjectStore

from fastapi import APIRouter, Depends


#
# API types
#
@dataclass_json
@dataclass
class GetFrameResult:
    frame: Frame
    content: List[Content]
    pre_render: Optional[str]


# FastAPI models
class FrameResponse(BaseModel):
    frame: dict
    content: List[dict]
    pre_render: Optional[str]

    class Config:
        arbitrary_types_allowed = True


router = APIRouter()


# Define routes
@router.get("/frame/{id}", response_model=dict)
@inject
async def get_frame(
    frames_api: Annotated[FramesApi, Depends(Provide[Container.frames_api])],
    prerender_db: Annotated[PreRenderDb, Depends(Provide[Container.prerender_db])],
    id: str,
):
    frame = frames_api.get(id)
    if not frame:
        raise HTTPException(status_code=404, detail="Frame not found")

    content = frames_api.get_content_for(id)
    pre_renders = prerender_db.get_for_frame(frame_id=id, limit=1)
    pre_render_hash = pre_renders[0].video_hash if pre_renders else None
    resp = GetFrameResult(frame=frame, content=content, pre_render=pre_render_hash)
    return resp.to_dict()


@router.get("/playlist/{id}.m3u8", response_class=Response)
@inject
async def get_playlist(
    frames_api: Annotated[FramesApi, Depends(Provide[Container.frames_api])],
    id: str,
    request: Request,
):
    if id == "all":
        version = "faded"
        content = frames_api._content_db.query(sys.maxsize)
    else:
        frame = frames_api.get(id)
        if not frame:
            raise HTTPException(status_code=404, detail="Frame not found")

        version = frame.options.get("preffered_version", "original")
        content = frames_api.get_content_for(id)

    res = "#EXTM3U\n"
    base_url = str(request.base_url)
    for c in content:
        content_id = c.versions.get(version, c.id)
        duration = (
            str(int(c.metadata["duration"]))
            if c.metadata and "duration" in c.metadata
            else ""
        )
        res += f"#EXINF:{duration}\n{base_url}video/{content_id}\n"
    res += "#EXT-X-ENDLIST"

    return Response(content=res, media_type="video/mp4")


@router.get("/video/{id}")
@inject
async def get_video(
    object_store: Annotated[ObjectStore, Depends(Provide[Container.object_store])],
    id: str,
):
    if object_store.exists(id):
        video_object = object_store.get(id)
        # TODO -- ensure that the content type is correct - maybe store it in the objectstore?
        return StreamingResponse(iter([video_object]), media_type="video/mp4")
    else:
        raise HTTPException(status_code=404, detail="Video not found")


@router.get("/thumbnail/{id}")
@inject
async def get_thumbnail(
    object_store: Annotated[ObjectStore, Depends(Provide[Container.object_store])],
    id: str,
):
    if object_store.exists(id):
        thumbnail_object = object_store.get(id)
        return StreamingResponse(iter([thumbnail_object]), media_type="image/jpeg")
    else:
        raise HTTPException(status_code=404, detail="Thumbnail not found")


@router.get("/api/gallery")
@inject
async def get_gallery_content(
    content_db: Annotated[ContentDb, Depends(Provide[Container.content_db])],
    page: int = Query(1, description="Page number, starting from 1"),
    page_size: int = Query(12, description="Number of items per page"),
):
    skip = (page - 1) * page_size
    limit = page_size
    
    # Get one more item than requested to check if there are more pages
    content_items = content_db.query(limit=limit + 1, created_after=None, created_before=None)
    
    # Check if there are more pages
    has_more = len(content_items) > limit
    # Truncate to requested page size
    if has_more:
        content_items = content_items[:limit]
    
    # Convert to dictionaries and add thumbnail URLs
    result = []
    for item in content_items:
        item_dict = item.to_dict()
        if item.thumbnail:
            item_dict["thumbnail_url"] = f"/thumbnail/{item.thumbnail}"
        result.append(item_dict)
    
    return {
        "items": result,
        "page": page,
        "page_size": page_size,
        "has_more": has_more
    }
