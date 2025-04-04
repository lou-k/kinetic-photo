from typing import Dict, Optional

from .object_store import ObjectStore
from .common import Content, ContentVersion, Resolution
from datetime import datetime


class ContentApi:
    def __init__(self, objectstore: ObjectStore):
        self.objectstore = objectstore

    def create(
        self,
        video_file: bytes,
        resolution: Optional[Resolution],
        created_at: datetime,
        source_id: Optional[str] = None,
        metadata: Optional[dict] = None,
        stream_id: Optional[int] = None,
        versions: Dict[ContentVersion, bytes] = {},
        pipeline_id: Optional[int] = None,
        poster_file: Optional[bytes] = None
    ) -> Content:
        hash = self.objectstore.add(video_file)
        versions = {k:self.objectstore.add(v) for k,v in versions.items()}
        versions[ContentVersion.Original] = hash
        
        # Store poster if provided
        poster_hash = None
        if poster_file:
            poster_hash = self.objectstore.add(poster_file)
            
        # sqllite3 throws when reading back a timestamp with timezone info
        # (see https://stackoverflow.com/questions/48614488/python-sqlite-valueerror-invalid-literal-for-int-with-base-10-b5911)
        # Here, we just make created_at match the local timezone to match how "processed_at" is stored.
        created_at = created_at.astimezone().replace(tzinfo=None)
        return Content(
            id=hash,
            created_at=created_at,
            processed_at=datetime.now(),
            resolution=resolution,
            pipeline_id=pipeline_id,
            source_id=source_id,
            metadata=metadata,
            stream_id=stream_id,
            versions=versions,
            poster=poster_hash
        )
