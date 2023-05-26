import logging.config
import sqlite3

from dependency_injector import containers, providers
from dependency_injector.wiring import Provide, inject

from db import initialize, IntegrationsDb, StreamsDb
from integrations import IntegrationsApi
from streams import StreamsApi


class Container(containers.DeclarativeContainer):
    config = providers.Configuration(
        yaml_files=["/etc/kinetic-photo/server/config.yml", "./config_dev.yml"]
    )

    logging = providers.Resource(
        logging.config.fileConfig,
        fname="logging.ini",
    )

    database_connection = providers.Resource(
        initialize,
        database=config.db.database

    )

    integrations_db = providers.Singleton(IntegrationsDb, database_connection)
    integrations_api = providers.Singleton(IntegrationsApi, integrations_db)

    streams_db = providers.Singleton(StreamsDb, database_connection)
    streams_api = providers.Singleton(StreamsApi, streams_db, integrations_api)


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
