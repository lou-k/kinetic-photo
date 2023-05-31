from typing import List, Optional

from disk_objectstore import Container
from .common import Content, Resolution
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
    ) -> Content:
        hash = self.objectstore.add_object(video_file)
        new_content = Content(
            id = hash,
            created_at=created_at,
            processed_at=datetime.now(),
            resolution=resolution,
            processor=processor,
            source_id=external_id,
            metadata=metadata,
            stream_id=stream_id
        )
        self.db.save(new_content)
        return new_content

    def query(
        self,
        limit: int,
        stream_id: Optional[int] = None,
        processor: Optional[str] = None,
        created_after: Optional[str] = None,
        created_before: Optional[str] = None,
    ) -> List[Content]:
        return self.db.query(limit, stream_id, processor, created_after, created_before)
