import logging
from datetime import datetime
from io import BytesIO
from typing import List

import magic
import pandas as pd
import PIL
from disk_objectstore import Container
from PIL import ExifTags, Image

from .common import Upload
from .db import UploadsDb


def get_exif_data(bytes: bytes) -> dict:
    """Extracts the exif data from the provided image and returns it as a dictionary.

    Args:
        bytes (bytes): The compressed jpeg image loaded into ram.

    Returns:
        dict: A dictionary of exif tag -> value
    """
    try:
        img = Image.open(BytesIO(bytes))
        exif_data = img.getexif()
        exif_data = {
            ExifTags.TAGS[k]: v for k, v in exif_data.items() if k in ExifTags.TAGS
        }
        for k, v in exif_data.items():
            match type(v):
                case PIL.TiffImagePlugin.IFDRational:
                    exif_data[k] = float(v)
                case default:
                    pass
        return exif_data
    except Exception as e:
        logging.warn(f"Could not get exif data, returning none...", exc_info=e)
        return {}


class UploadsApi:
    def __init__(self, db: UploadsDb, objectstore: Container):
        self.db = db
        self.objectstore = objectstore

    def add(self, file: bytes) -> Upload:
        """Ingests the provided bytes into the uploads data store.

        Args:
            file (bytes): The file to add

        Returns:
            Upload: An object with the information about this file.
        """
        content_type = magic.from_buffer(file, mime=True)
        metadata = {}
        if content_type.startswith("image"):
            metadata.update(get_exif_data(file))

        if "DateTime" in metadata:
            created_at = datetime.strptime(metadata["DateTime"], "%Y:%m:%d %H:%M:%S")
        else:
            created_at = datetime.now()

        hash = self.objectstore.add_object(file)

        logging.info(f"Metadata is {type(metadata)}: " + str(metadata))

        u = Upload(
            id=hash,
            created_at=created_at,
            uploaded_at=datetime.now(),
            content_type=content_type,
            metadata=metadata,
        )
        self.db.save(u)
        return u

    def remove(self, id: str) -> None:
        """Deletes the indicated upload from the database

        Args:
            id (str): The upload to delete.
        """
        self.objectstore.delete_objects([id])
        self.db.remove(id)

    def list(self) -> pd.DataFrame:
        """Lists all uploads in the database

        Returns:
            pd.DataFrame: A table of uploads.
        """
        return self.db.list()

    def query(self, limit: int, **kwargs) -> List[Upload]:
        """Queries the uploads database for specific uploads.

        Args:
            limit (int): How many items to return at most

        Returns:
            List[Upload]: The found uploads.
        """
        return self.db.query(limit, **kwargs)
