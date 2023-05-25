import glob
import json
import logging
import os
import sqlite3
from typing import Optional

import pandas as pd


def _update_database_if_needed(connection: sqlite3.Connection) -> None:
    # Get the current schema version
    with connection:
        current_version = connection.execute("PRAGMA schema_version;").fetchone()[0]
    logging.debug(f"Current version is {current_version}")

    # Update any schemas if necessary
    sql_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "db", "sql")
    for file_path in sorted(glob.glob(sql_dir + "/*.sql")):
        idx = int(os.path.basename(file_path)[0:3])
        if idx > current_version:
            logging.warn(f"Updating database to version {idx} with {file_path}")
            with connection:
                with open(file_path, "r") as sql_file:
                    connection.executescript(sql_file.read())


class DataStore:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection
        _update_database_if_needed(self.connection)

class StreamsDb(DataStore):
    def __init__(self, connection: sqlite3.Connection):
        super().__init__(connection=connection)
    
    def list(self) -> pd.DataFrame:
        """
        Lists all streams in the datastore.
        """
        with self.connection:
            return pd.read_sql_query("SELECT * FROM streams", self.connection, index_col="id")

    def get(self, id: int):
        with self.connection:
            return self.connection.execute(
                "SELECT * FROM streams WHERE id = ?", (id,)
            ).fetchone()

    def remove(self, id: int) -> None:
        """
        Removes a streams from the datastore.
        """
        with self.connection:
            self.connection.execute("DELETE FROM streams WHERE id = ?", (id,))

    def add(self, name: str, type: str, integration_id: Optional[int], params: Optional[dict], filters: Optional[dict]) -> int:
        """
        Saves a new streams to the datastore and returns it's id.
        """
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute(
                "INSERT INTO streams(name, type, integration_id, params_json, filters_json) VALUES(?, ?, ?, ?, ?)",
                (name, type, integration_id, params, filters),
            )
            return cursor.lastrowid


class IntegrationsDb(DataStore):
    def __init__(self, connection: sqlite3.Connection):
        super().__init__(connection=connection)

    def list(self) -> pd.DataFrame:
        """
        Lists all integrations in the datastore.
        """
        with self.connection:
            return pd.read_sql_query("SELECT * FROM integrations", self.connection, index_col="id")

    def get(self, id: int):
        with self.connection:
            return self.connection.execute(
                "SELECT * FROM integrations WHERE id = ?", (id,)
            ).fetchone()

    def remove(self, id: int) -> None:
        """
        Removes an integration from the datastore.
        """
        with self.connection:
            self.connection.execute("DELETE FROM integrations WHERE id = ?", (id,))

    def add(self, name: str, type: str, params) -> int:
        """
        Saves a new integration to the datastore and returns it's id.
        """
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute(
                "INSERT INTO integrations(name, type, params) VALUES(?, ?, ?)",
                (name, type, params),
            )
            return cursor.lastrowid
