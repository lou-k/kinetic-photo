from fastapi import FastAPI
from nicegui import ui

from kinetic_server.db import ContentDb

from ..frames import FramesApi
from . import gallery


class MainLayout:
    """Main layout component for the application UI"""

    def __init__(
        self, fastapi_app: FastAPI, frames_api: FramesApi, content_db: ContentDb
    ):
        """Initialize the main layout with components"""
        self.app = fastapi_app
        self.frames_api = frames_api
        self.content_db = content_db

        @ui.page("/")
        def show():
            with ui.header().classes(replace="row items-center") as header:
                ui.button(on_click=lambda: left_drawer.toggle(), icon="menu").props(
                    "flat color=white"
                )
                with ui.tabs() as tabs:
                    ui.tab("Frames", icon="panorama")
                    ui.tab("Gallery", icon="photo_library")

            with ui.footer(value=False) as footer:
                ui.label("Footer")

            with ui.left_drawer(value=False).classes("bg-blue-100") as left_drawer:
                ui.label("Side menu")

            with ui.page_sticky(position="bottom-right", x_offset=20, y_offset=20):
                ui.button(on_click=footer.toggle, icon="contact_support").props("fab")

            with ui.tab_panels(tabs, value="Gallery").classes("w-full"):
                with ui.tab_panel("Frames"):
                    frames = self.frames_api.list()
                    ui.table.from_pandas(frames)

                with ui.tab_panel("Gallery"):
                    gallery.render(self.content_db)

        # Initialize NiceGUI with FastAPI
        ui.run_with(
            self.app,
            favicon="📸",
            title="Kinetic Photo",
        )
