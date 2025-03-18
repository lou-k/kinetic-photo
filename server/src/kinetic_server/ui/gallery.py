from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple
from dataclasses_json import dataclass_json
from nicegui import ui

from kinetic_server.common import Content

from ..db import ContentDb


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


def _masory_grid():
    # Create a container with the masonry grid class
    ui.html(
        """
        <style>
            .masonry-grid {
                column-count: 6; /* Default for large screens */
                column-gap: 0;
            }
            @media (max-width: 600px) {
                .masonry-grid {
                    column-count: 2; /* Fewer columns on small screens */
                }
            }
            @media (min-width: 601px) and (max-width: 900px) {
                .masonry-grid {
                    column-count: 3; /* Medium screens */
                }
            }
        </style>
    """
    )
    return ui.element("div").classes("masonry-grid")


def _render_gallery_item(content: Content) -> None:
    """Render a single gallery item with lazy-loading video"""
    # Each item is wrapped in a div styled for masonry layout
    with ui.element("div").classes("masonry-item").style(
        "break-inside: avoid; margin: 0; padding: 0;"
    ):
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


def render(content_db: ContentDb, initial_query: GalleryQuery = GalleryQuery()):

    grid = _masory_grid()
    has_next = True
    state = initial_query

    def load_more():
        nonlocal state, has_next
        with grid:
            content, state, has_next = _next_page(state, content_db)
            for item in content:
                _render_gallery_item(item)

    load_more()
    if has_next:
        ui.button("Load More", on_click=load_more)
