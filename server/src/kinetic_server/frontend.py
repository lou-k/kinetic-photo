from typing import Annotated
from fastapi import Depends, FastAPI

from nicegui import app, ui

from .containers import Container
from .frames import FramesApi
from dependency_injector.wiring import Provide, inject


@inject
def init(fastapi_app: FastAPI, frames_api: Annotated[FramesApi, Depends(Provide[Container.frames_api])]) -> None:
    @ui.page('/')
    def show():
        
        with ui.header().classes(replace='row items-center') as header:
            ui.button(on_click=lambda: left_drawer.toggle(), icon='menu').props('flat color=white')
            with ui.tabs() as tabs:
                ui.tab('Frames', icon='panorama')

        with ui.footer(value=False) as footer:
            ui.label('Footer')

        with ui.left_drawer().classes('bg-blue-100') as left_drawer:
            ui.label('Side menu')

        with ui.page_sticky(position='bottom-right', x_offset=20, y_offset=20):
            ui.button(on_click=footer.toggle, icon='contact_support').props('fab')

        with ui.tab_panels(tabs, value='Frames').classes('w-full'):
            with ui.tab_panel('Frames'):
                frames = frames_api.list()
                ui.table.from_pandas(frames)
            with ui.tab_panel('B'):
                ui.label('Content of B')
            with ui.tab_panel('C'):
                ui.label('Content of C')

    ui.run_with(
        fastapi_app,
        favicon='📸',
        title='Kinetic Photo',
    )