from fastapi import FastAPI
from nicegui import ui

from kinetic_server.db import ContentDb

from ..frames import FramesApi
from ..streams import StreamsApi
from ..pipelines import PipelineApi
from . import gallery
from . import frames


class MainLayout:
    """Main layout component for the application UI"""

    def __init__(
        self, fastapi_app: FastAPI, frames_api: FramesApi, content_db: ContentDb,
        streams_api: StreamsApi, pipeline_api: PipelineApi
    ):
        """Initialize the main layout with components"""
        self.app = fastapi_app
        self.frames_api = frames_api
        self.content_db = content_db
        self.streams_api = streams_api
        self.pipeline_api = pipeline_api

        @ui.page("/")
        def show():
            # Detect if the user is on a mobile device and set padding to 0
            ui.run_javascript(
                """
                if (window.innerWidth <= 768) {
                    document.querySelector('.nicegui-content').classList.add('p-0', 'gap-0');
                }
                """
            )

            framesui = frames.FramesUI(frames_api, self.streams_api, self.pipeline_api)
            galleryui = gallery.GalleryUI(self.content_db)

            with ui.header().classes(replace="row items-center") as header:
                ui.button(on_click=lambda: left_drawer.toggle(), icon="menu").props(
                    "flat color=white"
                )
                with ui.tabs() as tabs:
                    ui.tab("Frames", icon="panorama")
                    ui.tab("Gallery", icon="photo_library")
                    to_show_drawer = {"Frames"}
                    def on_click(value):
                        nonlocal left_drawer, to_show_drawer
                        left_drawer.clear()
                        match value.value:
                            case "Frames":
                                framesui.render_drawer(left_drawer)
                                left_drawer.show()
                            case "Gallery":
                                left_drawer.hide()
                    tabs.on_value_change(on_click)

            with ui.footer(value=False) as footer:
                ui.label("Footer")

            left_drawer = ui.left_drawer(value=False).classes("bg-blue-100")
            with ui.page_sticky(position="bottom-right", x_offset=20, y_offset=20):
                ui.button(on_click=footer.toggle, icon="contact_support").props("fab")

            with ui.tab_panels(tabs, value="Frames").classes("w-full"):
                with ui.tab_panel("Frames"):
                    framesui.render()
                with ui.tab_panel("Gallery").style("padding-left: 0; padding-right: 0").classes("w-full"):
                    galleryui.render()

        # Initialize NiceGUI with FastAPI
        ui.run_with(
            self.app,
            favicon="📸",
            title="Kinetic Photo",
        )
