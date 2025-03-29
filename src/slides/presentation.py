from .api_types import Dimension

from .object import Object
from .page import Slide


class Presentation:

    def __init__(self, width: Dimension, height: Dimension):
        self.width = width
        self.height = height

        self._to_compile: list[Object] = []

    def slide(self, **kwargs) -> Slide:
        """
        Creates or updates a slide.

        If you want to update, pass in an object_id
        """

        default_kwargs = {
            "width": self.width,
            "height": self.height,
        }
        merged_kwargs = {**default_kwargs, **kwargs}
        slide = Slide(**merged_kwargs)

        self._to_compile.append(slide)

        return slide

    def compile(self) -> list[dict]:
        """
        Compiles changes into a batch update set of operations
        """

        updates = []

        for object in self._to_compile:
            updates += object.compile()

        return updates
