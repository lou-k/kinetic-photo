from datetime import datetime
from enum import Enum
from typing import Optional

from gphotospy.media import *
from jsonpath_ng.ext import parse

from common import Resolution, StreamMedia
from db import StreamsDb
from integrations import IntegrationsApi
from integrations.common import Integration


class StreamType(Enum):
    Google_Photos_Album = 1
    Google_Photos_Search = 2


class Stream:
    def __init__(self, id: int):
        self.id = id

    def __iter__(self):
        return self

    def __next__(self):
        ...


class Filter:
    def __init__(self, expression: str, over: Stream):
        self.over = over
        self.expression = expression

    def __iter__(self):
        self.over.__iter__()
        return self

    def __next__(self) -> StreamMedia:
        while True:
            media = next(self.over)
            if len(parse(self.expression).find([media.to_dict()])):
                return media


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


class GooglePhotosStream(Stream):
    def __init__(self, id: int, integration: Integration):
        super().__init__(id)
        self.integration = integration

    def __to_media__(self, m: MediaItem) -> StreamMedia:
        return StreamMedia(
            stream_id=self.id,
            is_video=m.is_video(),
            created_at=datetime.fromisoformat(m.metadata()["creationTime"]),
            resolution=Resolution(
                width=int(m.metadata()["width"]), height=int(m.metadata()["height"])
            ),
            url=m.get_url(for_download=True),
            identifier=m.val["id"],
            filename=m.val["filename"],
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
