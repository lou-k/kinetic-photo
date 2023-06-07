from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from dataclasses_json import config, dataclass_json
from disk_objectstore import Container as DiskContainer
from marshmallow import fields


@dataclass_json
@dataclass
class Resolution:
    """
    The resolution in pixels of a peice of media.
    """

    width: int
    height: int


@dataclass_json
@dataclass
class StreamMedia:
    """
    A piece of media produced by a stream
    """
    created_at: datetime = field(  # When the media was created
        metadata=config(
            encoder=datetime.isoformat,
            decoder=datetime.fromisoformat,
            mm_field=fields.DateTime(format="iso"),
        )
    )
    identifier: str  # The id of the media used by the source provider -- i.e., google photos id., or the hash if an upload.
    is_video: bool  # If True, this media is a video
    metadata: dict # A dictionary of metadata about this file. Contains resolution, filename, etc..
    stream_id: int  # Which stream this media came from
    url: Optional[str] = None  # The url of the media (if remote)


@dataclass_json
@dataclass
class Content:
    """
    A piece of content is a rendered video that will be displayed on the frame.
    """

    id: str  # The hash of the file in the object store
    created_at: datetime = field(  # When the media was created
        metadata=config(
            encoder=datetime.isoformat,
            decoder=datetime.fromisoformat,
            mm_field=fields.DateTime(format="iso"),
        )
    )
    processor: str  # The processor that made this content
    processed_at: datetime = field(  # When the media was created
        metadata=config(
            encoder=datetime.isoformat,
            decoder=datetime.fromisoformat,
            mm_field=fields.DateTime(format="iso"),
        )
    )
    metadata: Optional[dict] = None  # Other data that may be useful
    resolution: Optional[Resolution] = None  # Width and height of the video in pixels
    source_id: Optional[
        str
    ] = None  # The id used by the source provider -- i.e., google photos id.
    stream_id: Optional[int] = None  # Which stream contained the original media


class PipelineStatus(Enum):
    Successful = "Successful"
    Failed = "Failed"


@dataclass
class PipelineRun:
    id: int
    pipeline_id: int
    log_hash: str
    completed_at: datetime
    status: PipelineStatus


@dataclass
class Frame:
    id: str
    name: str
    options: dict


def initialize_objectstore(container: DiskContainer) -> None:
    if not container.is_initialised:
        container.init_container(clear=False)
