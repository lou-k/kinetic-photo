import logging.config
import os
import sqlite3

from dependency_injector import containers, providers
from dependency_injector.wiring import Provide, inject
from disk_objectstore import Container as DiskContainer

from kinetic_server.frames import FramesApi
from kinetic_server.uploads import UploadsApi

from .content import ContentApi
from .db import (ContentDb, FramesDb, IntegrationsDb, PipelineDb, StreamsDb, UploadsDb,
                 WrappedConnection)
from .integrations import IntegrationsApi
from .pipelines import PipelineApi, PipelineLoggerFactory
from .streams import StreamsApi


class Container(containers.DeclarativeContainer):
    config = providers.Configuration(
        yaml_files=["/etc/kinetic-photo/server/config.yml", "./config_dev.yml"]
    )

    logging = providers.Resource(
        logging.config.fileConfig,
        fname=os.path.join(os.path.dirname(__file__), "logging.ini"),
    )

    database_connection = providers.ThreadLocalSingleton(
        WrappedConnection,
        database=config.db.database,
        detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
    )
    object_store = providers.ThreadLocalSingleton(
        DiskContainer, config.objectstore.folder
    )

    integrations_db = providers.Singleton(IntegrationsDb, database_connection)
    integrations_api = providers.Singleton(IntegrationsApi, integrations_db)


    uploads_db = providers.Singleton(UploadsDb, database_connection)
    uploads_api = providers.Singleton(UploadsApi, uploads_db, object_store)

    streams_db = providers.Singleton(StreamsDb, database_connection)
    streams_api = providers.Singleton(StreamsApi, streams_db, integrations_api, uploads_api)

    content_db = providers.Singleton(ContentDb, database_connection)
    content_api = providers.Singleton(ContentApi, object_store)

    pipeline_db = providers.Singleton(PipelineDb, database_connection)
    pipeline_logger_factory = providers.Singleton(
        PipelineLoggerFactory, pipeline_db, object_store
    )
    pipeline_api = providers.Singleton(
        PipelineApi, pipeline_db, content_db, pipeline_logger_factory
    )

    frames_db = providers.Singleton(FramesDb, database_connection)
    frames_api = providers.Singleton(FramesApi, frames_db, content_db)


@inject
def example(api=Provide[Container.integrations_api]):
    return api


def init() -> Container:
    container = Container()
    container.init_resources()
    container.wire(modules=[__name__])
    return container


if __name__ == "__main__":
    print(init().config())
    example()
