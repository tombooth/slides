from typing import Optional
from uuid import uuid4

from .api_types import Dimension
from .base import Operation


class Object(Operation):
    object_id: str
    children: list[Operation]
    width: Dimension
    height: Dimension

    def __init__(
        self,
        object_id: Optional[str] = None,
        width: Optional[Dimension] = None,
        height: Optional[Dimension] = None,
        **kwargs,
    ):
        if object_id is not None:
            self.object_id = object_id
            self._new = False
        else:
            self.object_id = str(uuid4())
            self._new = True

        self.width = width
        self.height = height
        self.children = []

    def __call__(self, *children: list[Operation]):
        self.children = children
        return self
