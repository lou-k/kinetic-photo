import json
from enum import Enum

from ..db import IntegrationsDb

from .common import Integration
from .googlephotos import GooglePhotos


class IntegrationType(Enum):
    GOOGLEPHOTOS = GooglePhotos


class IntegrationsApi:
    def __init__(self, db: IntegrationsDb):
        self._db = db

    def list(self):
        return self._db.list()

    def get(self, id: int):
        _, _, typ, params = self._db.get(id)
        return self.from_params(IntegrationType[typ], json.loads(params))

    def from_params(self, type: IntegrationType, params):
        return type.value(**params)

    def remove(self, id: int):
        return self._db.remove(id)

    def add(self, name: str, integration: Integration):
        typ = next(t for t in IntegrationType if t.value == type(integration))
        params = json.dumps(integration.params())
        return self._db.add(name, typ.name, params)
