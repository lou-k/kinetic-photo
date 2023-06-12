"""
If steps require an external resource (database access, etc), use dependency injection to expose them here,
Don't ibnject them directly into the class constructors as they won't get serialized to the database.
"""
from dependency_injector.wiring import Provide, inject

from kinetic_server.db import ContentDb

from ..containers import Container
from disk_objectstore import Container as DiskContainer

from kinetic_server.content import ContentApi


@inject
def _content_api(api=Provide[Container.content_api]) -> ContentApi:
    return api


@inject
def _content_db(db=Provide[Container.content_db]) -> ContentDb:
    return db

@inject
def _object_store(os=Provide[Container.object_store]) -> DiskContainer:
    return os

container = Container()
container.init_resources()
container.wire(modules=[__name__])