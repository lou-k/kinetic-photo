from datetime import datetime
from typing import Optional
from .object_store import ObjectStore
from kinetic_server.common import AuxiliaryData
from kinetic_server.db import AuxiliaryCacheDb


class AuxiliaryCache:
    def __init__(self, db: AuxiliaryCacheDb, os: ObjectStore):
        self.db = db
        self.os = os

    def get(self, id: str, type: str) -> Optional[bytes]:
        """Returns the auxiluary data for the provided media if it exists in the cache.

        Args:
            id (str): The identifier of the stream media to get the data for.
            type (str): The type of data .

        Returns:
            Optional[bytes]: The data if found, None if it's not in the cache
        """
        di = self.db.get(id)
        return self.os.get(di.depth_hash) if di else None
        

    def save(self, id: str, type: str, auxiliary_data: bytes) -> AuxiliaryData:
        """Saves some new data to the cache.

        Args:
            id (str): The identifier of the stream media this data is for. 
            type (str): The type of data being saved.
            auxiliary_data (bytes): The data to save
        """
        hash = self.os.add(auxiliary_data)
        self.db.save(AuxiliaryData(id=id, type=type, computed_at=datetime.now(), file_hash=hash))
        return self.db.get(id, type)
