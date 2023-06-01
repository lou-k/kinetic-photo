import json
from enum import Enum

import pandas as pd

from ..db import IntegrationsDb
from .common import Integration
from .googlephotos import GooglePhotos


class IntegrationType(Enum):
    """Each supported integration should have a constant here indicating their type."""

    GOOGLEPHOTOS = GooglePhotos


class IntegrationsApi:
    """An API for managing integerations."""

    def __init__(self, db: IntegrationsDb):
        self._db = db

    def list(self) -> pd.DataFrame:
        """Lists all integrations in the database

        Returns:
            pd.DataFrame: A table of all integrations in the database.
        """
        return self._db.list()

    def get(self, id: int) -> Integration:
        """Retrieves an integeation from the database

        Args:
            id (int): The integration to get

        Returns:
            Integration: The integration oject instance
        """
        _, _, typ, params = self._db.get(id)
        return self.from_params(IntegrationType[typ], json.loads(params))

    def from_params(self, type: IntegrationType, params) -> Integration:
        """Re-serializes an integration of the provided type using the provided params.

        Args:
            type (IntegrationType): The type of integration object to create
            params (dict): The parameters to pass to the types constructor.

        Returns:
            Integration: The integration oject instance
        """
        return type.value(**params)

    def remove(self, id: int):
        """Deletes the indicated integration from the database

        Args:
            id (int): The id of the integration to delete.
        """
        return self._db.remove(id)

    def add(self, name: str, integration: Integration) -> int:
        """Saves a new integration in the database

        Args:
            name (str): The name of this integrtaion
            integration (Integration): An instance of the integration to persist.

        Returns:
            int: The id of the newly created intgeration
        """
        typ = next(t for t in IntegrationType if t.value == type(integration))
        params = json.dumps(integration.params())
        return self._db.add(name, typ.name, params)
