from datetime import datetime
from typing import Optional
from disk_objectstore import Container
from kinetic_server.common import DepthImage
from kinetic_server.db import DepthCacheDb


class DepthCache:
    def __init__(self, db: DepthCacheDb, os: Container):
        self.db = db
        self.os = os

    def get(self, id: str) -> Optional[bytes]:
        """Returns the depth map for the provided image if it exists in the cache.

        Args:
            id (str): The identifier of the stream media to get the depth for.

        Returns:
            Optional[bytes]: The depth image if found, None if it's not in the cache
        """
        di = self.db.get(id)
        return self.os.get_object_content(di.depth_hash) if di else None
        

    def save(self, id: str, depth_image: bytes) -> DepthImage:
        """Saves a new depth image to the cache.

        Args:
            id (str): The identifier of the stream media this depth was extracted for
            depth_image (bytes): The depth image for this media
        """
        hash = self.os.add_object(depth_image)
        self.db.save(DepthImage(id=id, extracted_at=datetime.now(), depth_hash=hash))
        return self.db.get(id)
