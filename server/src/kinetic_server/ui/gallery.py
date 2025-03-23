from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple
from dataclasses_json import dataclass_json
from nicegui import ui

from kinetic_server.common import Content

from ..db import ContentDb
import math


@dataclass_json
@dataclass
class GalleryQuery:
    created_before: str = datetime.now().isoformat()  # a datetime string
    limit: int = 24
    orientation: Optional[str] = None
    source_id: Optional[str] = None
    stream_id: Optional[int] = None
    pipeline_id: Optional[int] = None


def _next_page(
    state: GalleryQuery,
    content_db: ContentDb,
) -> Tuple[List[Content], GalleryQuery, bool]:
    content_items = content_db.query(**state.to_dict())

    # If we have items, update the state for the next query
    if len(content_items):
        next_state = GalleryQuery(**state.to_dict())
        next_state.created_before = content_items[-1].created_at.isoformat()

        # Check if there are more items after this batch
        next_items_check = content_db.query(**{**next_state.to_dict(), "limit": 1})
        has_next = len(next_items_check) > 0

        return content_items, next_state, has_next
    else:
        return content_items, state, False


def _masory_grid(column_width: int):
    return (
        ui.element("div")
        .style(
            f"""
            display: grid;
            grid-template-columns: repeat(auto-fill, {column_width}px);
            grid-auto-rows: 1px;
            overflow: hidden; 
            grid-row-gap: 0px;
            grid-column-gap: 0px;
        """
        ).classes("w-full")
    )


def _render_gallery_item(content: Content, column_width: int) -> None:
    """Render a single gallery item with lazy-loading video"""

    with ui.element("div") as grid_item:
        # If we can get the width and height of the content from the metadata,
        # set the aspect ratio in the css so masonry can know the true dimensions of the media.
        width = content.metadata.get("width")
        height = content.metadata.get("height")
        if width and height:
            aspect_ratio = int(width) / int(height)
            item_height = column_width / aspect_ratio
            # round item_height to nearest integer
            item_height = round(item_height)
            # grid_item.style(f"grid-row-end: span calc(width / {aspect_ratio});")
            grid_item.style(f"grid-row-end: span {item_height};")

        with ui.card().props("flat dense square").classes("q-pa-none"):
            # Define video URL based on content ID or preferred version
            video_url = f"/video/{content.id}"

            # Create poster URL if available
            poster_url = f"/poster/{content.poster}" if content.poster else None

            if poster_url:
                video = (
                    ui.video(video_url, controls=False, loop=True)
                    .props(f'poster={poster_url} preload="none" muted')
                    .classes("w-full h-auto")
                )
            else:
                video = (
                    ui.video(video_url, controls=False, loop=True)
                    .props('preload="none" muted')
                    .classes("w-full h-auto")
                )

            # Create a hover element that spans the entire video area
            hover_area = (
                ui.element("div")
                .classes("absolute inset-0 cursor-pointer")
                .style("z-index: 10; top: 0; left: 0; right: 0; bottom: 0")
            )

            # Create closures with the correct video reference by using default arguments
            def on_mouse_enter(vid=video):
                # Force load the video and play it on hover
                vid.run_method("play")

            def on_mouse_leave(vid=video):
                # Pause the video when mouse leaves
                vid.run_method("pause")

            # Attach mouse event handlers
            hover_area.on("mouseenter", on_mouse_enter)
            hover_area.on("mouseleave", on_mouse_leave)




class GalleryUI:

    def __init__(self, content_db: ContentDb):
        self.content_db = content_db
    
    def render(self, initial_query: GalleryQuery = GalleryQuery(), column_width=248):

        grid = _masory_grid(column_width)
        has_next = True
        state = initial_query

        def load_more():
            nonlocal state, has_next
            with grid:
                content, state, has_next = _next_page(state, self.content_db)
                for item in content:
                    _render_gallery_item(item, column_width)

        load_more()

        # Add a timer to check for scroll position
        async def check_scroll():
            # Check if the user has scrolled near the bottom of the page
            scrolled_to_bottom = await ui.run_javascript(
                "window.pageYOffset + window.innerHeight >= document.documentElement.scrollHeight - 100"
            )
            if scrolled_to_bottom and has_next:
                load_more()

        # Use a timer to periodically check the scroll position
        ui.timer(0.1, lambda: check_scroll())