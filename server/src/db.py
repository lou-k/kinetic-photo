import glob
import json
import logging
import os
from shutil import _StrOrBytesPathT
import sqlite3
from typing import List, Optional
from common import Content

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


def _set_pragmas(connection: sqlite3.Connection) -> None:
    with connection:
        connection.execute("PRAGMA foreign_keys = ON")


def initialize(**args) -> sqlite3.Connection:
    con = sqlite3.connect(**args)
    _update_database_if_needed(con)
    _set_pragmas(con)
    return con


class StreamsDb:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def list(self) -> pd.DataFrame:
        """
        Lists all streams in the datastore.
        """
        with self.connection:
            return pd.read_sql_query(
                "SELECT * FROM streams", self.connection, index_col="id"
            )

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

    def add(
        self,
        name: str,
        type: str,
        integration_id: Optional[int],
        params: Optional[dict],
        filters: Optional[dict],
    ) -> int:
        """
        Saves a new streams to the datastore and returns it's id.
        """
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute(
                "INSERT INTO streams(name, type, integration_id, params_json, filter) VALUES(?, ?, ?, ?, ?)",
                (name, type, integration_id, params, filters),
            )
            return cursor.lastrowid


class IntegrationsDb:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def list(self) -> pd.DataFrame:
        """
        Lists all integrations in the datastore.
        """
        with self.connection:
            return pd.read_sql_query(
                "SELECT * FROM integrations", self.connection, index_col="id"
            )

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


class ContenDb:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def save(self, c: Content):
        metadata = c.metadata
        if c.metadata:
            metadata = json.dumps(c.metadata)
        with self.connection:
            self.connection.execute(
                "REPLACE INTO content (id, created_at, height, width, external_id, metadata, stream_id) VALUES(?, ?, ?, ?, ?, ?, ?)",
                c.id,
                c.created_at,
                c.height,
                c.width,
                c.external_id,
                metadata,
                c.stream_id,
            )

    def query(
        self,
        limit: int,
        stream_id: Optional[int] = None,
        created_after: Optional[str] = None,
        created_before: Optional[str] = None,
    ) -> List[Content]:
        conditionals = [
            x
            for x in [
                ("stream_id = ?", stream_id),
                ("created_at > ?", created_after),
                ("created_at < ?", created_before),
            ]
            if x[1]
        ]

        where_clause = " AND ".join([c[0] for c in conditionals])
        parameters = tuple([c[1] for c in conditionals])

        query = "SELECT * FROM content "
        if len(conditionals):
            query += "WHERE " + where_clause
        query += " LIMIT ?"
        parameters += (limit,)

        with self.connection:
            results = self.connection.execute(query, parameters).fetchall()
        return [
            Content(
                id=id,
                created_at=created_at,
                width=width,
                height=height,
                external_id=external_id,
                metadata=metadata,
                stream_id=stream_id,
            )
            for (
                id,
                created_at,
                width,
                height,
                external_id,
                metadata,
                stream_id,
            ) in results
        ]
