from typing import Optional
from uuid import uuid4

from .api_types import Dimension


class Object:
    object_id: str
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

    def compile(self) -> list[dict]:
        raise NotImplementedError("Please implement compile()")
