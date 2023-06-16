from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Optional, List, Tuple

from dataclasses_json import config, dataclass_json
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


class ContentVersion:
    Original = "original"
    Faded = "faded"

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
    processed_at: datetime = field(  # When the media was created
        metadata=config(
            encoder=datetime.isoformat,
            decoder=datetime.fromisoformat,
            mm_field=fields.DateTime(format="iso"),
        )
    )
    versions: Dict[ContentVersion, str] # A map of version identifier -> object id for different versions of this media
    metadata: Optional[dict] = None  # Other data that may be useful
    pipeline_id: Optional[int] = None # The pipeline that made this content
    resolution: Optional[Resolution] = None  # Width and height of the video in pixels
    source_id: Optional[
        str
    ] = None  # The id used by the source provider -- i.e., google photos id.
    stream_id: Optional[int] = None  # Which stream contained the original media

class PipelineStatus(Enum):
    Successful = "Successful"
    Failed = "Failed"

class Orientation(Enum):
    Tall = "Tall"
    Wide = "Wide"
    Square = "Square"

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


@dataclass_json
@dataclass
class Upload:
    """A piece of media that was manually uploaded by the user.
    """
    id: str  # The hash of the file in the object store
    created_at: datetime = field(  # When the media was created
        metadata=config(
            encoder=datetime.isoformat,
            decoder=datetime.fromisoformat,
            mm_field=fields.DateTime(format="iso"),
        )
    )
    uploaded_at: datetime = field(  # When the media was uploaded
        metadata=config(
            encoder=datetime.isoformat,
            decoder=datetime.fromisoformat,
            mm_field=fields.DateTime(format="iso"),
        )
    )
    content_type: str # The mime type of this file
    metadata: Optional[dict]  # Other data that may be useful such as resolution, etc

@dataclass_json
@dataclass
class AuxiliaryData:
    id: str # The source_id (i.e., identifier from stream media) that this data was computed for
    computed_at:  datetime = field(  # When the data was computed
        metadata=config(
            encoder=datetime.isoformat,
            decoder=datetime.fromisoformat,
            mm_field=fields.DateTime(format="iso"),
        )
    )
    type: str
    file_hash: str # The object hash of this depth image in the object store


@dataclass_json
@dataclass
class PreRender:
    id: int
    frame_id: str
    created_at:  datetime = field(  # When the depth was extracted
        metadata=config(
            encoder=datetime.isoformat,
            decoder=datetime.fromisoformat,
            mm_field=fields.DateTime(format="iso"),
        )
    )
    video_hash: str
    video_ids: List[str]


def get_resolution_and_orientation(
    m: StreamMedia,
) -> Tuple[Optional[Resolution], Optional[Orientation]]:
    if "width" in m.metadata and "height" in m.metadata:
        resolution = Resolution(
            int(m.metadata["width"]),
            int(m.metadata["height"]),
        )
        if resolution.width > resolution.height:
            orientation = Orientation.Wide
        elif resolution.height > resolution.width:
            orientation = Orientation.Tall
        else:
            orientation = Orientation.Square
        return (resolution, orientation)
    else:
        return None, None
