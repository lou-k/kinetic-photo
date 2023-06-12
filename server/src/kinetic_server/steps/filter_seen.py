import logging
from typing import Optional, Union

from kinetic_server.common import Content, StreamMedia
from kinetic_server.steps.step import Step


class FilterSeen(Step):
    """Drops stream media that was already processed."""
    def __init__(self, pipeline_id: Optional[int]) -> None:
        """Creates a new filter that removes media if it was already processed.

        Args:
            pipeline_id (Optional[int]): If set, only media created by this pipeline is filtered out. 
                                         If None, media processed by any pipeline is filtered out.
        """
        self.pipeline_id = pipeline_id
        super().__init__()

    def __call__(
        self, media: Union[Content, StreamMedia]
    ) -> Union[Content, StreamMedia, None]:
        if type(media) != StreamMedia:
            raise Exception(
                f"FilterSeen can only be applied to StreamMedia but a {type(media)} was provided."
            )
        from ._apis import _content_db

        exists = len(
            _content_db().query(
                1, source_id=media.identifier, stream_id=media.stream_id,
                pipeline_id = self.pipeline_id
            )
        )
        if exists:
            logging.debug(f"Dropping media {media.identifier} as it was already processed.")
            return None
        else:
            return media
