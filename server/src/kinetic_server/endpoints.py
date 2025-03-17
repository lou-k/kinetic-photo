import sys
from dataclasses import dataclass
from typing import Annotated, List, Optional

from dataclasses_json import dataclass_json
from dependency_injector.wiring import Provide, inject
from fastapi import Request, Response, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .common import Content, Frame
from .containers import Container
from .db import PreRenderDb
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
