from typing import Optional
from uuid import uuid4

from .api_types import Dimension
from .base import Operation


class Object(Operation):
    object_id: str
    children: list[Operation]

    def __init__(
        self,
        object_id: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)

        if object_id is not None:
            self.object_id = object_id
            self._new = False
        else:
            self.object_id = str(uuid4())
            self._new = True

        self.children = []

    def __call__(self, *children: list[Operation]):
        self.children = children
        return self
