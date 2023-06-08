import logging
from datetime import datetime
from tempfile import NamedTemporaryFile
from typing import Iterator, List, Tuple

import pandas as pd
import tqdm
from disk_objectstore import Container

from .common import ContentVersion, Orientation, PipelineRun, PipelineStatus, Resolution, StreamMedia
from .content import ContentApi
from .db import PipelineDb
from .fader import fade_video
from .processors import Processor
from .rules import Rule


class PipelineLogger:
    """A PipelineLogger records all logging events made during a Pipeline's run to a file and,
    once the run is completed, saves that log along with the resulting status to the database.
    Thus it persists errors and processing information for inspection later.

    The logger is a context provider that returns a logging.Logger object. To use it:

    with pipeline_logger as logger:
        logger.info....

    Once the `with` clause completes the log is persisted to the data and object store.
    """

    def __init__(
        self, db: PipelineDb, objectstore: Container, pipeline_id: int, name: str
    ):
        self._db = db
        self._pipeline_id = pipeline_id
        self._objectstore = objectstore
        self._name = name

    def __enter__(self) -> logging.Logger:
        """
        Returns a logger that will be used to run this
        """
        self.logfile = NamedTemporaryFile()
        self.logger = logging.getLogger()
        self.handler = logging.FileHandler(self.logfile.name)
        self.handler.setFormatter(
            logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s")
        )
        self.logger.addHandler(self.handler)
        return self.logger

    def __exit__(self, exception_type, exception_value, traceback):
        """
        Closes the logging file and saves the data to the database
        """
        status = PipelineStatus.Successful
        if exception_value is not None:
            self.logger.error(
                f"Could not execute pipeline {self._name} ({self._pipeline_id}):"
            )
            self.logger.exception(exception_value, exc_info=True)
            status = PipelineStatus.Failed

        # Remove the  logging hanlder
        self.logger.removeHandler(self.handler)
        # Save the log to the objectstore
        with open(self.logfile.name, mode="rb") as fin:
            log_hash = self._objectstore.add_object(fin.read())

        # removes the temporary file
        self.logfile.close()

        # Save the run information to the database
        run_id = self._db.add_run(
            PipelineRun(
                id=0,
                pipeline_id=self._pipeline_id,
                log_hash=log_hash,
                completed_at=datetime.now(),
                status=status,
            )
        )

        logging.info(
            f"Finished running pipeline {self._name} ({self._pipeline_id}), recorded run {run_id} with status {status}"
        )

        return True


class PipelineLoggerFactory:
    """A factory for PipelineLoggers.
    This factory helps pipelines avoid passing around the PipelineDb and Container references.
    """

    def __init__(self, db: PipelineDb, object_store: Container):
        self._db = db
        self._object_store = object_store

    def __call__(self, pipeline: "Pipeline") -> PipelineLogger:
        return PipelineLogger(self._db, self._object_store, pipeline.id, pipeline.name)


class Pipeline:
    """Pipelines process media from input streams and creates kinetic photos. It does this via it's steps:
    a collection of (Rule, Processor) pairs that can create video clips for different kinds of content.

    Each piece of media is evaluated against each Rule and, if it complies, is passed to the corresponding Processor.
    If the Processor is successful and creates a video file, it is added to the Content database via the ContentApi
    and will be available to all Kinetic Frames.

    Each time a pipeline is invoked via __call__, it's log and resulting status will be saved to the "pipeline_runs" table in the database.
    See the PipelineApi for how to access these results.
    """

    def __init__(
        self,
        id: int,
        name: str,
        steps: List[Tuple[Rule, Processor]],
        content_api: ContentApi,
        logger_factory: PipelineLoggerFactory,
    ):
        """Creates an instance of a Pipeline object

        Args:
            id (int): The pipeline's id
            name (str): The Pipeline's name
            steps (List[Tuple[Rule, Processor]]): Steps in this pipeline
            content_api (ContentApi): The content api for saving content
            logger_factory (PipelineLoggerFactory): A logger factory used to create Pipeline loggers.
        """
        self.id = id
        self.name = name
        self.steps = steps
        self._logger_factory = logger_factory
        self._content_api = content_api

    def __str__(self):
        return f'Pipeline "{self.name}" ({self.id}).\n Steps:\n' + "\n".join(
            [f"if {s[0]} then {s[1]}" for s in self.steps]
        )

    def __call__(self, stream: Iterator[StreamMedia], limit: int = None) -> None:
        """Runs this Pipeline to convert stream media into kinetic photo content.

        Args:
            stream (Iterator[StreamMedia]): An iterator of media items to process.
            limit (int, optional): If set, only process this many items.

        Raises:
            Exception: If the pipeline fails all media an exception is thrown.
        """
        pipeline_logger = self._logger_factory(self)
        with pipeline_logger as logger:
            num_successful = 0
            num_failed = 0
            for i, media in tqdm.tqdm(enumerate(stream), total=limit):
                # stop if limit is reached
                if limit and i > limit:
                    logger.info(f"Processed {limit} pieces of media. Stopping...")
                    break

                # Check each rule to see if we can apply it
                for rule, processor in self.steps:
                    if rule(media):
                        logger.info(
                            f"Processing media {media.identifier} with processor {processor.name}..."
                        )
                        if len(self._content_api.query(1, source_id=media.identifier)):
                            logging.info(
                                f"Media {media.identifier} has already been processed. Skipping..."
                            )
                        else:
                            try:
                                # Process the media into a video file
                                video_bytes = processor(media)
                                if not video_bytes:
                                    logger.warning(
                                        f"Processor {processor} returned no bytes for media {media.identifier}..."
                                    )
                                else:
                                    if (
                                        "width" in media.metadata
                                        and "height" in media.metadata
                                    ):
                                        resolution = Resolution(
                                            int(media.metadata["width"]),
                                            int(media.metadata["height"]),
                                        )
                                        if resolution.width > resolution.height:
                                            orientation = Orientation.Wide
                                        elif resolution.height > resolution.width:
                                            orientation = Orientation.Tall
                                        else:
                                            orientation = Orientation.Square
                                        media.metadata[
                                            "orientation"
                                        ] = orientation.value
                                    else:
                                        resolution = None

                                    faded_bytes, video_duration = fade_video(
                                        video_bytes
                                    )
                                    media.metadata["duration"] = video_duration

                                    # Save the new content to the data store
                                    content = self._content_api.save(
                                        video_file=video_bytes,
                                        resolution=resolution,
                                        processor=processor.name,
                                        created_at=media.created_at,
                                        external_id=media.identifier,
                                        stream_id=media.stream_id,
                                        metadata=media.metadata,
                                        versions={
                                            ContentVersion.Faded: faded_bytes
                                        },
                                    )
                                    logger.info(f"Created new content {content.id}!")
                                num_successful += 1
                            except Exception as e:
                                logger.error(
                                    f"Failed to process media {media.identifier} with processor {processor}, pipeline run will be marked as failed.",
                                    e,
                                )
                                num_failed += 1
            if num_failed > 0 and num_successful == 0:
                # The processor is consistently failing, throw here to fail the pipeline run
                raise Exception(
                    f"Pipeline {self.name} ({self.id}) failed all media -- considering this run a failure. See logs for details."
                )


class PipelineApi:
    """Provides programatic tools for managing pipelines."""

    def __init__(
        self,
        db: PipelineDb,
        content_api: ContentApi,
        logger_factory: PipelineLoggerFactory,
    ):
        """Creates a new instance of the PipelineApi

        Args:
            db (PipelineDb): The pipeline database
            content_api (ContentApi): The content api used to create content
            logger_factory (PipelineLoggerFactory): A factory for creating pipeline loggers.
        """
        self._db = db
        self._content_api = content_api
        self._logger_factory = logger_factory

    def get(self, id: int) -> Pipeline:
        """Retrieves a pipeline by it's id

        Args:
            id (int): The pipeline's id

        Returns:
            Pipeline: An instantiated pipeline object that represents this pipeline from the database.
        """
        id, name, steps = self._db.get(id)
        return Pipeline(id, name, steps, self._content_api, self._logger_factory)

    def list(self) -> pd.DataFrame:
        """Lists all pipelines in the database.

        Returns:
            pd.DataFrame: A dataframe containing all pipeline information.
        """
        return self._db.list()

    def list_runs(self) -> pd.DataFrame:
        """Lists all of the pipeline runs in the database

        Returns:
            pd.DataFrame: A table of all pipeline runs in the database.
        """
        return self._db.list_runs()

    def create(self, name: str) -> Pipeline:
        """Creates a new pipeline with the provided name.

        Args:
            name (str): The human-language name for this pipeline

        Returns:
            Pipeline: An instantiated pipeline class representing the new pipeline you created.
        """
        id = self._db.create(name)
        return self.get(id)

    def add_step(self, pipeline_id: int, rule: Rule, processor: Processor) -> Pipeline:
        """Adds a step to the indicated pipeline

        Args:
            pipeline_id (int): The pipeline to add the step to.
            rule (Rule): The step's Rule.
            processor (Processor): The step's Processor.

        Returns:
            Pipeline: A new pipeline object with the provided step included.
        """
        self._db.add_step(pipeline_id=pipeline_id, rule=rule, processor=processor)
        return self.get(pipeline_id)
