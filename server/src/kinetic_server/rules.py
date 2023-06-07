import inspect
import json
import logging
import sys

from jsonpath_ng.ext import parse

from .common import StreamMedia


class Rule:
    """A Rule indicates if a peice of media should be kept based on sepcific conditions.
    For example, a rule may only approve images that have an embedded depth map, or those
    that appear to be portraits.

    Rules get paired with a Processor in pipelines -- thus a rule is meant to exclude
    content that the Processor shouldn't touch.
    """
    def __call__(self, media: StreamMedia) -> bool:
        """Applies this rule to the provided stream media and returns the result.

        Args:
            media (StreamMedia): The media to evaluate against this rule.

        Returns:
            bool: True if the media abides by the rule, and false otherwise
        """
        ...

    def __rep__(self):
        """Serialized this Rule into a string.

        Returns:
            str: A json encoded dictionary containing this Rule's classname and parameters.
        """
        return json.dumps({"type": self.__class__.__name__, "params": self.__dict__})
    
    def __str__(self):
        return self.__rep__()


class FilterRule(Rule):
    """A rule that uses json-path expressions to remove content.
    Specifically, https://pypi.org/project/jsonpath-ng/ is employed on each media item.
    If the expression matches the item, it's kept. Otherwise it's dropped.

    See https://github.com/h2non/jsonpath-ng for syntax

    This allows you to filter content based on the attributes of the stream media attributes (i.e., filename, etc)
    """
    def __init__(self, expression: str):
        """Creates a new FilterRule

        Args:
            expression (str): The jsonpath expression that is applied to each stream media. 
        """
        self.expression = expression

    def __call__(self, media: StreamMedia) -> bool:
        logging.debug(
            f"{type(self)} with expression {self.expression} processing media {media.identifier}"
        )
        keep = len(parse(self.expression).find([media.to_dict()])) > 0
        if keep:
            logging.debug(
                f"{type(self)} with expression {self.expression} keeping media {media.identifier}"
            )
        else:
            logging.debug(
                f"{type(self)} with expression {self.expression} dropping media {media.identifier}"
            )
        return keep


def rule_adapter(r: Rule) -> str:
    """sqlite3 adapter for Rule classes.

    Args:
        r (Rule): The Rule to serialize

    Returns:
        str: A serialized version of Rule r
    """
    return r.__rep__()


def rule_converter(s: str) -> Rule:
    """sqlite3 converter for Rule types.

    Args:
        s (str): A serialized version of a Rule.

    Returns:
        Rule: A de-serialized Rule.
    """
    d = json.loads(s)
    return eval(d["type"])(**(d["params"]))


def list_rules() -> dict:
    """Enumerates the Rules available. The superclass is not included.

    Returns:
        dict: A dictionary of Rule class name -> class object
    """
    return {
        name : obj
        for name, obj in inspect.getmembers(sys.modules[__name__], inspect.isclass)
        if issubclass(obj, Rule) and name != "Rule"
    }
