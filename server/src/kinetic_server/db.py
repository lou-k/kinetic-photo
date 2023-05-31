import glob
import json
import logging
import os
import sqlite3
from datetime import datetime
from typing import List, Optional, Tuple

import pandas as pd

from .common import Content, Frame, PipelineRun, PipelineStatus, Resolution
from .processors import (
    Processor,
    list_processors,
    processor_adapter,
    processor_converter,
)
from .rules import Rule, list_rules, rule_adapter, rule_converter


def _update_database_if_needed(connection: sqlite3.Connection) -> None:
    # Get the current schema version
    with connection:
        current_version = connection.execute("PRAGMA user_version;").fetchone()[0]
    logging.debug(f"Current version is {current_version}")

    # Update any schemas if necessary
    sql_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "db", "sql")
    for file_path in sorted(glob.glob(sql_dir + "/*.sql")):
        idx = int(os.path.basename(file_path)[0:3])
        if idx > current_version:
            logging.warning(f"Updating database to version {idx} with {file_path}")
            with connection:
                with open(file_path, "r") as sql_file:
                    connection.executescript(sql_file.read())
                connection.execute("PRAGMA user_version = " + str(idx))


def _set_pragmas(connection: sqlite3.Connection) -> None:
    with connection:
        connection.execute("PRAGMA foreign_keys = ON")


def pipeline_status_adapter(s: PipelineStatus) -> str:
    return s.name


def pipeline_status_converter(s: str) -> PipelineStatus:
    return PipelineStatus[str(s, "utf-8")]


def _setup_types() -> None:
    sqlite3.register_adapter(Rule, rule_adapter)
    for subclass in list_rules().values():
        sqlite3.register_adapter(subclass, rule_adapter)
    sqlite3.register_converter("Rule", rule_converter)
    sqlite3.register_adapter(Processor, processor_adapter)
    for subclass in list_processors().values():
        sqlite3.register_adapter(subclass, processor_adapter)
    sqlite3.register_converter("Processor", processor_converter)
    sqlite3.register_adapter(PipelineStatus, pipeline_status_adapter)
    sqlite3.register_converter("PipelineStatus", pipeline_status_converter)


class WrappedConnection(sqlite3.Connection):
    def __init__(self, **args):
        _setup_types()
        super().__init__(**args)
        _update_database_if_needed(self)
        _set_pragmas(self)


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
    ) -> int:
        """
        Saves a new streams to the datastore and returns it's id.
        """
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute(
                "INSERT INTO streams(name, type, integration_id, params_json) VALUES(?, ?, ?, ?)",
                (name, type, integration_id, params),
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


class ContentDb:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def save(self, c: Content):
        metadata = c.metadata
        if c.metadata:
            metadata = json.dumps(c.metadata)
        with self.connection:
            self.connection.execute(
                "REPLACE INTO content (id, created_at, height, width, source_id, metadata, stream_id, processor) VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    c.id,
                    c.created_at,
                    c.resolution.height if c.resolution else None,
                    c.resolution.width if c.resolution else None,
                    c.source_id,
                    metadata,
                    c.stream_id,
                    c.processor,
                ),
            )

    def query(
        self,
        limit: int,
        stream_id: Optional[int] = None,
        processor: Optional[str] = None,
        created_after: Optional[str] = None,
        created_before: Optional[str] = None,
    ) -> List[Content]:
        conditionals = [
            x
            for x in [
                ("stream_id == ?", stream_id),
                ("processor == ?", processor),
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
        query += " ORDER BY created_at DESC LIMIT ?"
        parameters += (limit,)

        with self.connection:
            results = self.connection.execute(query, parameters).fetchall()
        return [
            Content(
                id=id,
                created_at=created_at,
                resolution=Resolution(width, height) if width and height else None,
                source_id=source_id,
                processor=processor,
                metadata=json.loads(metadata) if metadata else None,
                stream_id=stream_id,
            )
            for (
                id,
                created_at,
                height,
                width,
                source_id,
                metadata,
                stream_id,
                processor,
            ) in results
        ]


class FramesDb:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def list(self) -> pd.DataFrame:
        """
        Lists all frames in the datastore.
        """
        with self.connection:
            return pd.read_sql_query(
                "SELECT * FROM frames", self.connection, index_col="id"
            )

    def get(self, id: str) -> Frame:
        with self.connection:
            res = self.connection.execute(
                "SELECT * FROM frames WHERE id = ?", (id,)
            ).fetchone()
            if res:
                id, name, options = res
                return Frame(id, name, json.loads(options))
            else:
                return None

    def remove(self, id: str) -> None:
        """
        Removes a frame from the datastore.
        """
        with self.connection:
            self.connection.execute("DELETE FROM frames WHERE id = ?", (id,))

    def add(self, id: str, name: str, **options) -> Frame:
        """
        Saves a new frame to the datastore.
        """
        with self.connection:
            self.connection.execute(
                "INSERT INTO frames(id, name, options) VALUES(?, ?, ?)",
                (id, name, json.dumps(options)),
            )
        return self.get(id)


class PipelineDb:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def list(self) -> pd.DataFrame:
        """
        Lists all pipelines in the datastore.
        """
        with self.connection:
            return pd.read_sql_query(
                "SELECT * FROM pipelines", self.connection, index_col="id"
            )

    def list_runs(self) -> pd.DataFrame:
        """
        Lists all pipeline runs in the datastore.
        """
        with self.connection:
            return pd.read_sql_query(
                "SELECT * FROM pipeline_runs", self.connection, index_col="id"
            )

    def get(
        self, pipeline_id: int
    ) -> Optional[Tuple[int, str, List[Tuple[Rule, Processor]]]]:
        with self.connection:
            res = self.connection.execute(
                "SELECT * FROM pipelines WHERE id = ?", (pipeline_id,)
            ).fetchone()
        if res:
            id, name = res
            return (id, name, self.get_steps(pipeline_id))
        else:
            return None

    def get_steps(self, pipeline_id: int) -> List[Tuple[Rule, Processor]]:
        with self.connection:
            return self.connection.execute(
                "SELECT rule, processor FROM pipeline_steps WHERE pipeline_id = ?",
                (pipeline_id,),
            ).fetchall()

    def create(self, name: str) -> int:
        """
        Creates a new pipeline
        """
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute(
                "INSERT INTO pipelines(name) VALUES(?)",
                (name,),
            )
            return cursor.lastrowid

    def add_step(self, pipeline_id: int, rule: Rule, processor: Processor) -> int:
        """
        Adds a step to a pipeline.
        """
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute(
                "INSERT INTO pipeline_steps(pipeline_id, rule, processor) VALUES(?, ?, ?)",
                (pipeline_id, rule, processor),
            )
            return cursor.lastrowid

    def get_runs(
        self,
        pipeline_id: Optional[int],
        status: Optional[PipelineStatus],
        bookmark: Optional[int],
        limit: Optional[int],
    ) -> List[PipelineRun]:
        """Queries the database for pipeline run results. Newer runs are at the top of the list.

        Args:
            pipeline_id (Optional[int]): The pipeline to see runs for. If None, all pipelines are considered.
            status (Optional[PipelineStatus]): Only find runs that have this status.
            bookmark (Optional[int]): Use for pagniation -- only show runs with a rowid less than this value.
            limit (Optional[int]): Return at most this many runs.

        Returns:
            List[PipelineRun]: Any runs found from the database that match this criteria.
        """
        conditionals = [
            x
            for x in [
                ("pipeline_id == ?", pipeline_id),
                ("status == ?", status),
                ("id < ?", bookmark),
            ]
            if x[1]
        ]

        query = "SELECT * FROM pipeline_runs"
        if len(conditionals):
            query += "WHERE " + (" AND ".join([c[0] for c in conditionals]))
        query += " ORDER BY id DESC"
        parameters = tuple([c[1] for c in conditionals])
        if limit:
            query += " LIMIT ?"
            parameters += (limit,)

        with self.connection:
            results = self.connection.execute(query, parameters).fetchall()
            if results:
                return [PipelineRun(*r) for r in results]
            else:
                return None

    def get_run(self, run_id: int) -> PipelineRun:
        result = self.connection.execute(
            "SELECT * FROM pipeline_runs WHERE id=?",
            (run_id,),
        ).fetchone()
        return PipelineRun(*result) if result else None

    def add_run(self, run: PipelineRun) -> int:
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute(
                "INSERT INTO pipeline_runs(pipeline_id, log_hash, status, completed_at) VALUES(?, ?, ?, ?)",
                (run.pipeline_id, run.log_hash, run.status, run.completed_at),
            )
            return cursor.lastrowid
