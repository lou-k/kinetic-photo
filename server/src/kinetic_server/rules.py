import inspect
import json
import logging
import sys

from jsonpath_ng.ext import parse

from .common import StreamMedia


class Rule:
    def __call__(self, media: StreamMedia) -> bool:
        """
        Applies this rule to the provided stream media and returns:
        True if the media abides by the rule
        False if the media should be rejected
        """
        ...

    def __rep__(self):
        return json.dumps({"type": self.__class__.__name__, "params": self.__dict__})


class FilterRule(Rule):
    def __init__(self, expression: str):
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
    return r.__rep__()


def rule_converter(s: str) -> Rule:
    d = json.loads(s)
    return eval(d["type"])(**(d["params"]))


def list_rules() -> dict:
    return {
        name : obj
        for name, obj in inspect.getmembers(sys.modules[__name__], inspect.isclass)
        if issubclass(obj, Rule) and name != "Rule"
    }
