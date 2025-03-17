import logging
import urllib.request
from typing import Optional, Tuple

from kinetic_server.common import Content, StreamMedia, get_resolution_and_orientation
from kinetic_server.steps.step import ContentCreator

class CopyVideo(ContentCreator):
    """A simple creator that just copies video from streams into the content library."""

    def __init__(self):
        pass

    def create(self, m: StreamMedia) -> Optional[Content]:
        """Downloads the provided video clip if present.

        Args:
            media (StreamMedia): The stream media (hoppefully) containing a video.

        Returns:
            Optional[bytes]: The content created or None if stream media is an image.
        """
        if not m.is_video:
            logging.info(
                f"Skipping media {m.filename} from stream {m.stream_id} since it is not a video."
            )
            return None

        from ._apis import _object_store

        os = _object_store()

        # Get the video orientation and resolution
        resolution, orientation = get_resolution_and_orientation(m)
        metadata = m.metadata
        if orientation:
            metadata["orientation"] = orientation.value

        # Download the video if it's a url
        if m.url:
            logging.info(f"Downloading {m.url}....")
            try:
                response = urllib.request.urlopen(m.url)
                video_bytes = response.read()
            except Exception as e:
                logging.warning(
                    f"Could not download {m.url} for media {m.identifier}..", exc_info=e
                )
                return None
        # Load the video if it's an upload
        elif os.exists(m.identifier):
            video_bytes = os.get(m.identifier)
        else:
            logging.info(
                f"Could not download or find a video file for {m.identifier} .."
            )
            return None
        
        # Get the video poster
        poster_bytes = None
        if "poster_url" in metadata:
            logging.info(f"Downloading {metadata['poster_url']}....")
            try:
                response = urllib.request.urlopen(metadata["poster_url"])
                poster_bytes = response.read()
            except Exception as e:
                logging.warning(
                    f"Could not download {metadata['poster_url']} for media {m.identifier}..", exc_info=e
                )
        
        # Create the content
        return self.content_api.create(
            video_file=video_bytes,
            resolution=resolution,
            created_at=m.created_at,
            source_id=m.identifier,
            stream_id=m.stream_id,
            metadata=metadata,
            poster_file=poster_bytes
        )
