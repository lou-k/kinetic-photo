import glob
import json
import logging
import os
import sqlite3
from datetime import datetime
from typing import List, Optional, Tuple

import pandas as pd

from .common import (Content, DepthImage, Frame, PipelineRun, PipelineStatus,
                     PreRender, Resolution, Upload)
from .steps import Step, list_steps, step_adapter, step_converter


def _update_database_if_needed(connection: sqlite3.Connection) -> None:
    # Get the current schema version
    with connection:
        current_version = connection.execute("PRAGMA user_version;").fetchone()[0]
    logging.debug(f"Current version is {current_version}")

    # Update any schemas if necessary
    sql_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "db", "sql")
    with connection:
        for file_path in sorted(glob.glob(sql_dir + "/*.sql")):
            idx = int(os.path.basename(file_path)[0:3])
            if idx > current_version:
                logging.warning(f"Updating database to version {idx} with {file_path}")
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
    sqlite3.register_adapter(Step, step_adapter)
    for subclass in list_steps().values():
        sqlite3.register_adapter(subclass, step_adapter)
    sqlite3.register_converter("Step", step_converter)
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
        versions = json.dumps(c.versions)
        with self.connection:
            # sqllite3 throws when reading back a timestamp with timezone info
            # (see https://stackoverflow.com/questions/48614488/python-sqlite-valueerror-invalid-literal-for-int-with-base-10-b5911)
            # Just check that the values passed don't have timezone info
            if c.created_at.tzinfo is not None:
                raise Exception(
                    f"Due to an sqlite bug, created_at must have no timezone"
                )
            if c.processed_at.tzinfo is not None:
                raise Exception(
                    f"Due to an sqlite bug, processed_at must have no timezone"
                )
            self.connection.execute(
                "REPLACE INTO content (id, created_at, processed_at, height, width, source_id, metadata, stream_id, pipeline_id, versions) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    c.id,
                    c.created_at,
                    c.processed_at,
                    c.resolution.height if c.resolution else None,
                    c.resolution.width if c.resolution else None,
                    c.source_id,
                    metadata,
                    c.stream_id,
                    c.pipeline_id,
                    versions,
                ),
            )

    def query(
        self,
        limit: int,
        source_id: Optional[str] = None,
        stream_id: Optional[int] = None,
        pipeline_id: Optional[int] = None,
        created_after: Optional[str] = None,
        created_before: Optional[str] = None,
        orientation: Optional[str] = None,
    ) -> List[Content]:
        conditionals = [
            x
            for x in [
                ("source_id == ?", source_id),
                ("stream_id == ?", stream_id),
                ("pipeline_id == ?", pipeline_id),
                ("created_at > ?", created_after),
                ("created_at < ?", created_before),
                ("json_extract(metadata, '$.orientation') == ?", orientation),
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
                processed_at=processed_at,
                resolution=Resolution(width, height) if width and height else None,
                source_id=source_id,
                pipeline_id=pipeline_id,
                metadata=json.loads(metadata) if metadata else None,
                stream_id=stream_id,
                versions={k: v for k, v in json.loads(versions).items()},
            )
            for (
                id,
                created_at,
                height,
                metadata,
                pipeline_id,
                processed_at,
                source_id,
                stream_id,
                width,
                versions,
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

    def get(self, pipeline_id: int) -> Optional[Tuple[int, int, str, List[Step]]]:
        with self.connection:
            res = self.connection.execute(
                "SELECT * FROM pipelines WHERE id = ?", (pipeline_id,)
            ).fetchone()
        if res:
            id, stream_id, name = res
            return (id, stream_id, name, self.get_steps(pipeline_id))
        else:
            return None

    def get_steps(self, pipeline_id: int) -> List[Step]:
        with self.connection:
            return [
                s[0]
                for s in self.connection.execute(
                    "SELECT step FROM pipeline_steps WHERE pipeline_id = ? ORDER BY id ASC",
                    (pipeline_id,),
                ).fetchall()
            ]

    def create(self, name: str, stream_id: int) -> int:
        """
        Creates a new pipeline
        """
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute(
                "INSERT INTO pipelines(name, stream_id) VALUES(?, ?)",
                (name, stream_id),
            )
            return cursor.lastrowid

    def add_step(self, pipeline_id: int, step: Step) -> int:
        """
        Adds a step to a pipeline.
        """
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute(
                "INSERT INTO pipeline_steps(pipeline_id, step) VALUES(?, ?)",
                (pipeline_id, step),
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


class UploadsDb:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def list(self) -> pd.DataFrame:
        """
        Lists all uploads in the datastore.
        """
        with self.connection:
            return pd.read_sql_query(
                "SELECT * FROM uploads", self.connection, index_col="id"
            )

    def get(self, id: str) -> Optional[Upload]:
        """Looks up a single upload by id

        Args:
            id (str): The upload to look up

        Returns:
            Optional[Upload]: The upload if found or None otherwise
        """
        res = self.query(1, id=id)
        if len(res):
            return res[0]
        else:
            return None

    def remove(self, id: str) -> None:
        """
        Removes an upload from the datastore.
        """
        with self.connection:
            self.connection.execute("DELETE FROM uploads WHERE id = ?", (id,))

    def save(self, u: Upload):
        """Stores a new upload in the database

        Args:
            u (Upload): The upload to store
        """
        metadata = u.metadata
        if u.metadata:
            metadata = json.dumps(u.metadata)
        with self.connection:
            # sqllite3 throws when reading back a timestamp with timezone info
            # (see https://stackoverflow.com/questions/48614488/python-sqlite-valueerror-invalid-literal-for-int-with-base-10-b5911)
            # Just check that the values passed don't have timezone info
            if u.created_at.tzinfo is not None:
                raise Exception(
                    f"Due to an sqlite bug, created_at must have no timezone"
                )
            if u.uploaded_at.tzinfo is not None:
                raise Exception(
                    f"Due to an sqlite bug, uploaded_at must have no timezone"
                )
            self.connection.execute(
                "REPLACE INTO uploads (id, created_at, uploaded_at, metadata, content_type) VALUES(?, ?, ?, ?, ?)",
                (u.id, u.created_at, u.uploaded_at, metadata, u.content_type),
            )

    def query(
        self,
        limit: int,
        created_after: Optional[str] = None,
        created_before: Optional[str] = None,
        uploaded_after: Optional[str] = None,
        uploaded_before: Optional[str] = None,
        id: Optional[str] = None,
    ) -> List[Upload]:
        """Queries for uploads from the database.

        Args:
            limit (int): Return at most this many uploads.

        Returns:
            List[Upload]: Any uploads that were found.
        """
        conditionals = [
            x
            for x in [
                ("id == ", id),
                ("created_at > ?", created_after),
                ("created_at < ?", created_before),
                ("uploaded_at > ?", uploaded_after),
                ("uploaded_at < ?", uploaded_before),
            ]
            if x[1]
        ]

        where_clause = " AND ".join([c[0] for c in conditionals])
        parameters = tuple([c[1] for c in conditionals])

        query = "SELECT * FROM uploads "
        if len(conditionals):
            query += "WHERE " + where_clause
        query += " ORDER BY created_at DESC LIMIT ?"
        parameters += (limit,)

        with self.connection:
            results = self.connection.execute(query, parameters).fetchall()
        return [
            Upload(
                id=id,
                created_at=created_at,
                uploaded_at=uploaded_at,
                metadata=json.loads(metadata) if metadata else None,
                content_type=content_type,
            )
            for (id, created_at, uploaded_at, metadata, content_type) in results
        ]


class DepthCacheDb:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def get(self, id: int) -> Optional[DepthImage]:
        """
        Gets a depth image from the datastore.
        """
        with self.connection:
            res = self.connection.execute(
                "SELECT * FROM depth_cache WHERE id = ?", (id,)
            ).fetchone()
        return DepthImage(*res) if res else None

    def save(self, d: DepthImage):
        """Stores a depth image in the database"""
        with self.connection:
            # sqllite3 throws when reading back a timestamp with timezone info
            # (see https://stackoverflow.com/questions/48614488/python-sqlite-valueerror-invalid-literal-for-int-with-base-10-b5911)
            # Just check that the values passed don't have timezone info
            if d.extracted_at.tzinfo is not None:
                raise Exception(
                    f"Due to an sqlite bug, extracted_at must have no timezone"
                )
            self.connection.execute(
                "REPLACE INTO depth_cache (id, extracted_at, depth_hash) VALUES(?, ?, ?)",
                (d.id, d.extracted_at, d.depth_hash),
            )


class PreRenderDb:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def get_for_frame(self, frame_id: str, limit: int) -> List[PreRender]:
        with self.connection:
            return [
                PreRender(
                    id=id,
                    frame_id=frame_id,
                    created_at=created_at,
                    video_hash=video_hash,
                    video_ids=json.loads(video_ids),
                )
                for (
                    id,
                    frame_id,
                    created_at,
                    video_hash,
                    video_ids,
                ) in self.connection.execute(
                    "SELECT * FROM pre_renders WHERE frame_id = ? ORDER BY created_at DESC limit ?",
                    (frame_id, limit),
                ).fetchall()
            ]

    def create(self, frame_id: str, video_hash: str, video_ids: List[str]) -> PreRender:
        """Stores a depth image in the database"""
        with self.connection:
            self.connection.execute(
                "INSERT INTO pre_renders (frame_id, created_at, video_hash, video_ids) VALUES(?, ?, ?, ?)",
                (frame_id, datetime.now(), video_hash, json.dumps(video_ids)),
            )
            return self.get_for_frame(frame_id, 1)[0]

    def delete(self, id: int) -> None:
        with self.connection:
            self.connection.execute(
                "DROP FROM pre_renders WHERE id = ?", (id,)
            )