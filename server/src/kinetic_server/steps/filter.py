import logging
from typing import Union

from jsonpath_ng.ext import parse

from kinetic_server.common import Content, StreamMedia
from kinetic_server.steps.step import Step


class Filter(Step):
    """A step that uses json-path expressions to remove content.
    Specifically, https://pypi.org/project/jsonpath-ng/ is employed on each media item.
    If the expression matches the item, it's kept. Otherwise it's dropped.

    See https://github.com/h2non/jsonpath-ng for syntax

    This allows you to filter content based on the attributes of the stream media attributes (i.e., filename, etc)
    """

    def __init__(self, expression: str):
        """Creates a new FilterStep

        Args:
            expression (str): The jsonpath expression that is applied to each stream media.
        """
        self.expression = expression

    def __call__(self, media: Union[StreamMedia, Content]) -> bool:
        logging.debug(
            f"{type(self)} with expression {self.expression} processing media {media.identifier}"
        )
        if len(parse(self.expression).find([media.to_dict()])) > 0:
            logging.debug(
                f"{type(self)} with expression {self.expression} keeping media {media.identifier}"
            )
            return media
        else:
            logging.debug(
                f"{type(self)} with expression {self.expression} dropping media {media.identifier}"
            )
            return None
