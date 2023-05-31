import logging
from datetime import datetime
from tempfile import NamedTemporaryFile
from typing import Iterator, List, Tuple

import pandas as pd
from disk_objectstore import Container
import tqdm

from .common import PipelineRun, PipelineStatus, StreamMedia
from .content import ContentApi
from .db import PipelineDb
from .processors import Processor
from .rules import Rule


class PipelineLogger:
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
    def __init__(self, db: PipelineDb, object_store: Container):
        self._db = db
        self._object_store = object_store

    def __call__(self, pipeline: "Pipeline") -> PipelineLogger:
        return PipelineLogger(self._db, self._object_store, pipeline.id, pipeline.name)


class Pipeline:
    def __init__(
        self,
        id: int,
        name: str,
        steps: List[Tuple[Rule, Processor]],
        content_api: ContentApi,
        logger_factory: PipelineLoggerFactory,
    ):
        self.id = id
        self.name = name
        self.steps = steps
        self._logger_factory = logger_factory
        self._content_api = content_api

    def __call__(self, stream: Iterator[StreamMedia], limit: int = None) -> None:
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
                        try:
                            # Process the media into a video file
                            video_bytes = processor(media)
                            if not video_bytes:
                                logger.warning(
                                    f"Processor {processor} returned no bytes for media {media.identifier}..."
                                )
                            else:
                                # Save the new content to the data store
                                content = self._content_api.save(
                                    video_file=video_bytes,
                                    resolution=media.resolution,
                                    processor=processor.name,
                                    created_at=media.created_at,
                                    external_id=media.identifier,
                                    stream_id=media.stream_id,
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
    def __init__(
        self,
        db: PipelineDb,
        content_api: ContentApi,
        logger_factory: PipelineLoggerFactory,
    ):
        self._db = db
        self._content_api = content_api
        self._logger_factory = logger_factory

    def get(self, id: int) -> Pipeline:
        id, name, steps = self._db.get(id)
        return Pipeline(id, name, steps, self._content_api, self._logger_factory)

    def list(self) -> pd.DataFrame:
        return self._db.list()

    def list_runs(self) -> pd.DataFrame:
        return self._db.list_runs()

    def create(self, name: str) -> Pipeline:
        id = self._db.create(name)
        return self.get(id)

    def add_step(self, pipeline_id: int, rule: Rule, processor: Processor) -> Pipeline:
        self._db.add_step(pipeline_id=pipeline_id, rule=rule, processor=processor)
        return self.get(pipeline_id)
