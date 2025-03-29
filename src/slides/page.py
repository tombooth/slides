from typing import Optional

from .base import Context
from .object import Object


class Page(Object):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class Slide(Page):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def compile(self, context: Optional[Context] = None) -> list[dict]:
        if context is None:
            context = Context()

        context.push(self)

        if self._new:
            requests = [{"createSlide": {"objectId": self.object_id}}]
        else:
            requests = [
                {
                    "deleteObject": {
                        "objectId": self.object_id,
                    }
                },
                {"createSlide": {"objectId": self.object_id}},
            ]

        return requests + [
            request
            for child in self.children
            for request in child.compile(context=context)
        ]


def slide(**kwargs) -> Slide:
    return Slide(**kwargs)
