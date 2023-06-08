from enum import Enum
from typing import Dict, List, Optional

from disk_objectstore import Container
from .common import Content, ContentVersion, Resolution
from .db import ContentDb
from datetime import datetime


class ContentApi:
    def __init__(self, db: ContentDb, objectstore: Container):
        self.db = db
        self.objectstore = objectstore

    def save(
        self,
        video_file: bytes,
        resolution: Optional[Resolution],
        processor: str,
        created_at: datetime,
        external_id: Optional[str] = None,
        metadata: Optional[dict] = None,
        stream_id: Optional[int] = None,
        versions: Dict[ContentVersion, bytes] = {}
    ) -> Content:
        hash = self.objectstore.add_object(video_file)
        versions = {k:self.objectstore.add_object(v) for k,v in versions.items()}
        versions[ContentVersion.Original] = hash
        # sqllite3 throws when reading back a timestamp with timezone info
        # (see https://stackoverflow.com/questions/48614488/python-sqlite-valueerror-invalid-literal-for-int-with-base-10-b5911)
        # Here, we just make created_at match the local timezone to match how "processed_at" is stored.
        created_at = created_at.astimezone().replace(tzinfo=None)
        new_content = Content(
            id=hash,
            created_at=created_at,
            processed_at=datetime.now(),
            resolution=resolution,
            processor=processor,
            source_id=external_id,
            metadata=metadata,
            stream_id=stream_id,
            versions=versions
        )
        self.db.save(new_content)
        return new_content
    
    def query(
        self,
        limit: int,
        source_id: Optional[str] = None,
        stream_id: Optional[int] = None,
        processor: Optional[str] = None,
        created_after: Optional[str] = None,
        created_before: Optional[str] = None,
    ) -> List[Content]:
        return self.db.query(limit, source_id, stream_id, processor, created_after, created_before)
