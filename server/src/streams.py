from enum import Enum
from typing import Optional

from gphotospy.media import *

from db import StreamsDb
from integrations import IntegrationsApi
from integrations.common import Integration


class StreamType(Enum):
    Google_Photos_Album = 1
    Google_Photos_Search = 2


class Stream:
    def __iter__(self):
        return self

    def __next__(self):
        ...


class StreamsApi:
    def __init__(self, db: StreamsDb, integrations_api: IntegrationsApi):
        self._db = db
        self._integrations = integrations_api

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
        filter: Optional[dict],
    ) -> int:
        if params:
            params = json.dumps(params)
        if filter:
            filter = json.dumps(filter)
        return self._db.add(name, typ.name, integration_id, params, filter)

    def get(self, id: int) -> Stream:
        id, name, typ, integration_id, params, filter = self._db.get(id)
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
                return GooglePhotosAlbumStream(integration=integration, **params)
            case StreamType.Google_Photos_Search:
                if not integration:
                    raise Exception(
                        f'Stream {id} with name "{name}" should have a google photos integration.'
                    )
                return GooglePhotosSearchStream(integration=integration, **params)


class GooglePhotosStream(Stream):
    def __init__(self, integration: Integration):
        self.integration = integration

    def __next__(self):
        # TODO -- convert to common image type
        return next(self.iterator)


class GooglePhotosAlbumStream(GooglePhotosStream):
    def __init__(self, integration: Integration, album_id: str):
        super().__init__(integration)
        self.album_id = album_id

    def __iter__(self):
        with self.integration as gp:
            self.iterator = Media(gp).search_album(self.album_id)
        return self


class GooglePhotosSearchStream(GooglePhotosStream):
    def __init__(
        self, integration: Integration, filter: Optional[str] = None, exclude: Optional[str] = None
    ):
        super().__init__(integration)
        # we'll call eval here to convert the filter and exclusions into the proper gphotospy types.
        # this isn't ideal... perhaps we should switch away from gphotospy and use the api directly...
        if filter:
            filter = eval(filter)
        if exclude:
            exclude = eval(exclude)
        self.filter = filter
        self.exclude = exclude

    def __iter__(self):
        with self.integration as gp:
            self.iterator = Media(gp).search(self.filter, self.exclude)
        return self
