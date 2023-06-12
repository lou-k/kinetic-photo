import json
from typing import Optional, Union

from kinetic_server.common import Content, StreamMedia

class Step:
    """A step performs some kind of operation on either stream media (i.e., source images or videos) or content (i.e., kinetic photos).

    Each step may have different input requirements or parameters, so they could reject photos
    based on their content, type, etc.
    """

    def __rep__(self) -> str:
        """Serialized this step into a string.

        Returns:
            str: A json encoded dictionary containing this steps classname and parameters.
        """

        return json.dumps({"type": self.__class__.__name__, "params": self.__dict__})

    def __str__(self) -> str:
        return self.__rep__()

    def __call__(
        self, media: Union[Content, StreamMedia]
    ) -> Union[Content, StreamMedia, None]:
        """Processes the provided media, if possible, and returns the input to the next
        step in the pipeline.

        Args:
            media (StreamMedia): The media to generate a kinetic photo from.

        Returns:
            Union[Content, StreamMedia, None]: Returns:
                * None if the pipeline should stop.
                * Content if content was created by this step
                * StreamMedia if a stream media was augmented by this step.
        """
        ...

    @property
    def name(self) -> str:
        """Returns the step name. This may change if we have hot-loadable steps or steps with different arguments.


        Returns:
            str: The name of this step
        """
        return self.__class__.__name__

class ContentCreator(Step):
    """A Content Creator is a step that takes a StreamMedia and creates a piece of content."""

    def create(self, m: StreamMedia) -> Optional[Content]:
        """Creates some content (i.e., a kinetic photo) from the provided stream media.

        Args:
            m (StreamMedia): The media to create the content from

        Returns:
            Optional[Content]: A piece of content that was created, or None if the creation failed.
        """
        ...

    def __call__(
        self, media: Union[Content, StreamMedia]
    ) -> Union[Content, StreamMedia, None]:
        if type(media) != StreamMedia:
            raise TypeError(
                f"Creators can only process Stream Media but a {type(media)} was passed."
            )
        return self.create(media)

    @property
    def content_api(self):
        from ._apis import _content_api

        return _content_api()


class ContentAugmentor(Step):
    """A Content augmentor is a kind of step that adds new fields to existing content."""

    def augment(self, c: Content) -> Content:
        """Augments content (i.e., a kinetic photo) with some new info.

        Args:
            c (Content): The content to augment

        Returns:
            Content: The augmented content if successful or c if something went wrong.
        """
        ...

    def __call__(
        self, media: Union[Content, StreamMedia]
    ) -> Union[Content, StreamMedia, None]:
        if type(media) != Content:
            raise TypeError(
                f"Creators can only process Content but a {type(media)} was passed."
            )
        return self.augment(media)