import copy
import sys
from datetime import datetime
from enum import Enum
from typing import Optional

from gphotospy.media import *
from jsonpath_ng.ext import parse

from .common import StreamMedia, Upload
from .db import StreamsDb
from .integrations import IntegrationsApi
from .integrations.common import Integration
from .uploads import UploadsApi
import logging


class StreamType(Enum):
    Google_Photos_Album = 1
    Google_Photos_Search = 2
    Uploads = 3


class Stream:
    def __init__(self, id: int):
        self.id = id

    def __iter__(self):
        return self

    def __next__(self):
        ...

class StreamsApi:
    def __init__(
        self, db: StreamsDb, integrations_api: IntegrationsApi, uploads_api: UploadsApi
    ):
        self._db = db
        self._integrations = integrations_api
        self._uploads_api = uploads_api

    def remove(self, id: int) -> None:
        self._db.remove(id)

    def list(self):
        return self._db.list()

    def add(
        self,
        name: str,
        typ: StreamType,
        integration_id: Optional[int],
        params: Optional[dict],
    ) -> int:
        if params:
            params = json.dumps(params)
        return self._db.add(name, typ.name, integration_id, params)

    def get(self, id: int) -> Stream:
        id, name, typ, integration_id, params = self._db.get(id)
        typ = StreamType[typ]

        if params:
            params = json.loads(params)
        else:
            params = {}

        if integration_id:
            integration = self._integrations.get(integration_id)

        match typ:
            case StreamType.Google_Photos_Album:
                if not integration:
                    raise Exception(
                        f'Stream {id} with name "{name}" should have a google photos integration.'
                    )
                return GooglePhotosAlbumStream(id, integration, **params)
            case StreamType.Google_Photos_Search:
                if not integration:
                    raise Exception(
                        f'Stream {id} with name "{name}" should have a google photos integration.'
                    )
                return GooglePhotosSearchStream(id, integration, **params)
            case StreamType.Uploads:
                return UploadsStream(id, self._uploads_api, **params)


class GooglePhotosStream(Stream):
    def __init__(self, id: int, integration: Integration):
        super().__init__(id)
        self.integration = integration

    def __to_media__(self, m: MediaItem) -> StreamMedia:
        # Metadata commonly returned from google has width, height, photo info (camera make, model, etc)
        metadata = copy.deepcopy(m.metadata())

        # Flatten the "photo" metadata into the og dict.
        if "photo" in metadata:
            metadata.update(metadata["photo"])
            del metadata["photo"]

        # Flatten the "video" metadata into the og dict.
        if "video" in metadata:
            metadata.update(metadata["video"])
            del metadata["video"]

        # Include the filename in the meta data
        metadata["filename"] = m.val["filename"]

        # remove the creation date
        created_at = metadata["creationTime"]
        del metadata["creationTime"]

        # add the thumbnail url
        if "baseUrl" in m.val:
            metadata["thumbnail_url"] = m.val["baseUrl"]

        return StreamMedia(
            created_at=datetime.fromisoformat(created_at),
            identifier=m.val["id"],
            is_video=m.is_video(),
            metadata=metadata,
            stream_id=self.id,
            url=m.get_url(for_download=True),
        )

    def __next__(self):
        return self.__to_media__(MediaItem(next(self.iterator)))


class GooglePhotosAlbumStream(GooglePhotosStream):
    def __init__(self, id: int, integration: Integration, album_id: str):
        super().__init__(id, integration)
        self.album_id = album_id

    def __iter__(self):
        with self.integration as gp:
            self.iterator = Media(gp).search_album(self.album_id)
        return self


class GooglePhotosSearchStream(GooglePhotosStream):
    def __init__(
        self,
        id: int,
        integration: Integration,
        filter: Optional[str] = None,
        exclude: Optional[str] = None,
    ):
        super().__init__(id, integration)
        # we'll call eval here to convert the filter and exclusions into the proper gphotospy types.
        # this isn't ideal... perhaps we should switch away from gphotospy and use the api directly...
        logging.info("filter is " + str(type(filter)) + " with value: " + str(filter))
        if filter:
            if isinstance(filter, list):
                filter = [eval(f) for f in filter]
            else:
                filter = eval(filter)
        if exclude:
            if isinstance(exclude, list):
                exclude = [eval(f) for f in exclude]
            else:
                exclude = eval(exclude)
        self.filter = filter
        self.exclude = exclude

    def __iter__(self):
        with self.integration as gp:
            self.iterator = Media(gp).search(self.filter, self.exclude)
        return self


class UploadsStream(Stream):
    """A stream of uploaded media."""

    def __init__(self, id: int, uploads: UploadsApi):
        self.id = id
        self.api = uploads

    def __iter__(self):
        self.iterator = self.api.query(limit=sys.maxsize)
        return self

    def __to_media__(self, upload: Upload) -> StreamMedia:
        return StreamMedia(
            created_at=upload.created_at,
            identifier=upload.id,
            is_video=upload.content_type.startswith("video"),
            metadata=upload.metadata,
            stream_id=self.id,
            url=None,
        )

    def __next__(self):
        return self.__to_media__(next(self.iterator))
