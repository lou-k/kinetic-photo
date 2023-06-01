
from typing import List, Optional
from kinetic_server.common import Content, Frame
from kinetic_server.content import ContentApi
from kinetic_server.db import FramesDb
import uuid

class FrameOptions:
    QUERY_PARAMS = "content_query_params"
    DEFAULT_LIMIT = 100000

class FramesApi:

    def __init__(self, db: FramesDb, content_api: ContentApi):
        self._db = db
        self._content_api = content_api
    
    def get_content_for(self, id: str, limit: Optional[int] = None) -> List[Content]:
        """Materializes content for the provided kinetic photo frame.
        Newer content appears at the top of the list.

        Args:
            id (str): The id of the frame.
            limit (Optional[int], optional): If set, only return this number of results. Defaults to None.

        Returns:
            List[Content]: The content for this frame.
        """
        frame = self._db.get(id)
        query_params = frame.options.get(FrameOptions.QUERY_PARAMS, {})
        limit = limit if limit else FrameOptions.DEFAULT_LIMIT
        return self._content_api.query(
            limit=limit,
            **query_params
        )
        
    def get(self, id: str) -> Frame:
        """Retrieves the frame with the provided identifier

        Args:
            id (str): The id of the frame to lookup

        Returns:
            Frame: The found frame
        """
        return self._db.get(id)
    
    def list(self):
        return self._db.list()
    
    def remove(self, id: str) -> None:
        return self._db.remove(id)

    def add(self, name: str, **options) -> Frame:
        id = str(uuid.uuid1())
        return self._db.add(
            id,
            name,
            **options
        )