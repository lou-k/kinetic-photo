from nicegui import ui
import json

from kinetic_server.frames import FramesApi, FrameOptions
from kinetic_server.common import Frame, Orientation
from kinetic_server.streams import StreamsApi
from kinetic_server.pipelines import PipelineApi
from nicegui.page_layout import Drawer
from . import gallery

def _frame_editor(frame: Frame, frames_api: FramesApi, streams_api: StreamsApi, pipeline_api: PipelineApi):
    
    """Create editor for frame options"""
    with ui.row().classes("q-mb-md"):
        ui.label(f"ID: {frame.id}")
        ui.button("Copy").props("flat dense icon=content_copy").on_click(
            lambda: ui.clipboard.write(frame.id)
        )

    # Initialize options from frame (or with defaults)
    options = frame.options.copy() if frame.options else {}

    # Extract query params for content
    query_params = options.get(FrameOptions.QUERY_PARAMS, {})

    # Shuffle toggle
    shuffle = ui.switch(
        "Shuffle content", value=options.get(FrameOptions.SHUFFLE, False)
    )

    # Content limit
    limit = ui.number(
        "Content limit",
        value=options.get("limit", FrameOptions.DEFAULT_LIMIT),
        min=1,
        max=FrameOptions.DEFAULT_LIMIT
    )

    # Content Query Parameters in an expansion
    with ui.expansion("Content Query Parameters").classes("q-mt-md"):
        with ui.row():
            # Orientation dropdown
            orientations = ["Any", "Tall", "Wide", "Square"]
            orientation = ui.select(
                label="Orientation",
                options=orientations,
                value=query_params.get("orientation", "Any"),
            ).style("width: 100px;")

            
            # Stream ID
            # Get all available streams for dropdown
            streams_df = streams_api.list()
            stream_options = {
                **{-1: "All"},
                **{id: r["name"] for id, r in streams_df.iterrows()},
            }
            stream_id_dropdown = ui.select(
                label="Stream",
                options=stream_options,
                value=int(query_params.get("stream_id", -1)),
            ).style("width: 100px;")

            # Pipeline ID
            # Get all available pipelines for dropdown
            pipelines_df = pipeline_api.list()
            pipeline_options = {
                **{-1: "All"},
                **{id: r["name"] for id, r in pipelines_df.iterrows()},
            }

            pipeline_id_dropdown = (
                ui.select(
                    label="Pipeline",
                    options=pipeline_options,
                    value=int(query_params.get("pipeline_id", -1)),
                ).style("width: 100px;")
            )

        # Date filters
        with ui.row():
            with ui.input(
                "Created After", value=query_params.get("created_after", "")
            ) as created_after:
                with ui.menu().props("no-parent-event") as menu_after:
                    with ui.date().bind_value(created_after):
                        with ui.row().classes("justify-end"):
                            ui.button("Close", on_click=menu_after.close).props("flat")
                with created_after.add_slot("append"):
                    ui.icon("edit_calendar").on("click", menu_after.open).classes(
                        "cursor-pointer"
                    )

            # with ui.row():
            with ui.input(
                "Created Before", value=query_params.get("created_before", "")
            ) as created_before:
                with ui.menu().props("no-parent-event") as menu_before:
                    with ui.date().bind_value(created_before):
                        with ui.row().classes("justify-end"):
                            ui.button("Close", on_click=menu_before.close).props("flat")
                with created_before.add_slot("append"):
                    ui.icon("edit_calendar").on("click", menu_before.open).classes(
                        "cursor-pointer"
                    )

    with ui.row().classes("q-mt-md justify-end"):

        def save_options():
            # Collect all options
            new_query_params = {}

            # For stream ID, only add if a specific value was selected (not "All")
            if stream_id_dropdown.value >= 0:
                new_query_params["stream_id"] = stream_id_dropdown.value

            # For pipeline ID, only add if a specific value was selected (not "All")
            if pipeline_id_dropdown.value >= 0:
                new_query_params["pipeline_id"] = pipeline_id_dropdown.value

            if created_after.value:
                new_query_params["created_after"] = created_after.value

            if created_before.value:
                new_query_params["created_before"] = created_before.value

            if orientation.value and orientation.value != "Any":
                new_query_params["orientation"] = orientation.value

            # Update frame options
            new_options = {}
            new_options[FrameOptions.SHUFFLE] = shuffle.value
            new_options[FrameOptions.QUERY_PARAMS] = new_query_params
            if limit.value != FrameOptions.DEFAULT_LIMIT:
                new_options["limit"] = limit.value

            frame.options = new_options

            # Save the frame with new options
            frames_api.update(frame)
            ui.notify(f"Frame '{frame.name}' updated")

        ui.button("Save", on_click=save_options).props("color=primary")


class FramesUI:
    def __init__(
        self, frames_api: FramesApi, streams_api: StreamsApi, pipeline_api: PipelineApi
    ):
        self.frames_api = frames_api
        self.streams_api = streams_api
        self.pipeline_api = pipeline_api
        self.card = None
        self.list = None

    def render(self):
        self.card = ui.card().classes("w-full")

    def show_frame(self, f):
        self.card.clear()
        with self.card:
            ui.markdown(f"## {f.name}")
            with ui.column():
                _frame_editor(f, self.frames_api, self.streams_api, self.pipeline_api)
            # with ui.column():
            #     gallery.render(self.frames_api._content_db, initial_query=gallery.GalleryQuery(
                    
            #     ))

    def render_drawer(self, left_drawer: Drawer):
        with left_drawer:
            self.list = ui.list()
            with self.list:
                for frame in self.frames_api._db.search():
                    ui.item(frame.name, on_click=lambda f=frame: self.show_frame(f))
            def new_frame():
                with self.list:
                    frame = self.frames_api.add("New Frame")
                    left_drawer.clear()
                    self.render_drawer(left_drawer)
                    self.show_frame(frame)
                    # ui.item(frame.name, on_click=lambda f=frame: self.show_frame(f))
                    # self.show_frame(frame)
            ui.button("New", on_click=new_frame).props("color=primary")
