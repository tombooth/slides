from typing import Optional

from .api_types import Type
from .base import Context
from .object import Object


class Shape(Object):
    type: Type

    def __init__(self, type: Type, **kwargs):
        super().__init__(**kwargs)
        self.type = type

    def compile(self, context: Optional[Context] = None) -> list[dict]:
        if context is None:
            context = Context()

        context.push(self)

        if self._new:
            requests = [
                {"createShape": {"objectId": self.object_id, "shapeType": self.type}}
            ]
        else:
            requests = []

        return requests + [
            request
            for child in self.children
            for request in child.compile(context=context)
        ]


class TextBox(Shape):
    def __init__(self, **kwargs):
        kwargs["type"] = Type.TEXT_BOX
        super().__init__(**kwargs)


def text_box(**kwargs) -> TextBox:
    return TextBox(**kwargs)
