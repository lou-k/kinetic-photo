import logging.config
import os
import sqlite3

from dependency_injector import containers, providers
from dependency_injector.wiring import Provide, inject
from disk_objectstore import Container as DiskContainer

from kinetic_server.frames import FramesApi

from .content import ContentApi
from .db import ContentDb, FramesDb, IntegrationsDb, PipelineDb, StreamsDb, WrappedConnection
from .integrations import IntegrationsApi
from .pipelines import PipelineApi, PipelineLoggerFactory
from .streams import StreamsApi


def _initialize_objectstore(folder: str) -> DiskContainer:
    ds = DiskContainer(folder)
    if not ds.is_initialised:
        logging.warning(f"Datastore {folder} doesn't exist, creating...")
        ds.init_container(clear=False)
    return ds


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

    object_store = providers.Resource(
        _initialize_objectstore, config.objectstore.folder
    )

    integrations_db = providers.Singleton(IntegrationsDb, database_connection)
    integrations_api = providers.Singleton(IntegrationsApi, integrations_db)

    streams_db = providers.Singleton(StreamsDb, database_connection)
    streams_api = providers.Singleton(StreamsApi, streams_db, integrations_api)

    content_db = providers.Singleton(ContentDb, database_connection)
    content_api = providers.Singleton(ContentApi, content_db, object_store)

    pipeline_db = providers.Singleton(PipelineDb, database_connection)
    pipeline_logger_factory = providers.Singleton(
        PipelineLoggerFactory,
        pipeline_db,
        object_store
    )
    pipeline_api = providers.Singleton(
        PipelineApi, pipeline_db, content_api, pipeline_logger_factory
    )

    frames_db = providers.Singleton(
        FramesDb,
        database_connection
    )
    frames_api = providers.Singleton(
        FramesApi,
        frames_db,
        content_api
    )


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
