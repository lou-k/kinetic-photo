from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

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
    stream_id: int  # Which stream this media came from
    is_video: bool  # If True, this media is a video
    created_at: datetime = field(  # When the media was created
        metadata=config(
            encoder=datetime.isoformat,
            decoder=datetime.fromisoformat,
            mm_field=fields.DateTime(format="iso"),
        )
    )
    resolution: Resolution  # The resolution of the media
    external_id: Optional[
        str
    ] = None  # The id of the media used by the source provider -- i.e., google photos id.
    url: Optional[str] = None  # The url of the media (if remote)
    object_hash: Optional[
        str
    ] = None  # The hash of the media (if stored locally in the object store)
