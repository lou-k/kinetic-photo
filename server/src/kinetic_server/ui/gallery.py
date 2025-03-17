from typing import Dict, Any, List
from nicegui import ui

from ..db import ContentDb


class Gallery:
    """Gallery component for displaying video content with hover-based lazy loading"""
    
    def __init__(self, content_db: ContentDb):
        """Initialize the gallery with required dependencies"""
        self.content_db = content_db
        self.state = {
            'items': [],
            'page': 1,
            'has_more': True,
            'loading': False,
            'grid': None
        }
    
    def load_page(self, page: int = 1, append: bool = False) -> None:
        """Load a page of gallery content directly from ContentDb"""
        if self.state['loading']:
            return
            
        self.state['loading'] = True
        try:
            # Get page_size + 1 items to check if there are more pages
            page_size = 12
            skip = (page - 1) * page_size
            limit = page_size + 1
            
            # Query content from database directly
            content_items = self.content_db.query(limit=limit, skip=skip)
            
            # Check if there are more pages
            has_more = len(content_items) > page_size
            # Truncate to requested page size
            if has_more:
                content_items = content_items[:page_size]
            
            # Convert Content objects to dictionaries
            items = []
            for item in content_items:
                item_dict = item.to_dict()
                # Add thumbnail and video URLs if available
                if item.thumbnail:
                    item_dict["thumbnail_url"] = f"/thumbnail/{item.thumbnail}"
                # Add video URL based on content ID or versions
                item_dict["video_url"] = f"/video/{item.id}"
                
                # If there's a faded version available, use that instead
                if item.versions and "faded" in item.versions:
                    item_dict["video_url"] = f"/video/{item.versions['faded']}"
                items.append(item_dict)
            
            # Update gallery state
            if append:
                self.state['items'].extend(items)
            else:
                self.state['items'] = items
            
            self.state['page'] = page
            self.state['has_more'] = has_more
            
            # Create or clear the gallery grid
            if self.state['grid'] is None:
                self.state['grid'] = ui.grid(columns=4).classes('w-full gap-4')
            
            # if not append:
            #     self.state['grid'].clear()
            
            # Add new items
            with self.state['grid']:
                items_to_display = items if append else self.state['items']
                for item in items_to_display:
                    self._render_gallery_item(item)
                    
        finally:
            self.state['loading'] = False
    
    def _render_gallery_item(self, item: Dict[str, Any]) -> None:
        """Render a single gallery item with lazy-loading video"""
        with ui.card().classes('w-full'):
            # Show video content with lazy loading
            # Use thumbnail as poster if available and only load video when user hovers
            with ui.card_section().classes('relative w-full h-48 video-container') as container:
                if 'thumbnail_url' in item and item['thumbnail_url']:
                    video = ui.video(item['video_url'], controls=False, loop=True).props(f'poster={item["thumbnail_url"]} preload="none" muted').classes('w-full h-48')
                else:
                    video = ui.video(item['video_url'], controls=False, loop=True).props('preload="none" muted').classes('w-full h-48')
                
                # Create a hover element that spans the entire video area
                hover_area = ui.element('div').classes('absolute inset-0 cursor-pointer').style('z-index: 10; top: 0; left: 0; right: 0; bottom: 0')
                
                # Create closures with the correct video reference by using default arguments
                def on_mouse_enter(vid=video):
                    # Force load the video and play it on hover
                    # vid.run_method('load')
                    vid.run_method('play')
                    
                def on_mouse_leave(vid=video):
                    # Pause the video when mouse leaves
                    vid.run_method('pause')
                    
                # Attach mouse event handlers
                hover_area.on('mouseenter', on_mouse_enter)
                hover_area.on('mouseleave', on_mouse_leave)
    
    def load_more(self) -> None:
        """Load the next page of gallery content"""
        if not self.state['has_more'] or self.state['loading']:
            return
        
        self.state['page'] += 1
        self.load_page(self.state['page'], append=True)
    
    def render(self) -> None:
        """Render the gallery component with load more button"""
        # Initialize gallery
        self.load_page()
        load_more_button = ui.button('Load More', on_click=self.load_more).props('outline')