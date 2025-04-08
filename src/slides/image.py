from matplotlib.axes import Axes
from matplotlib.figure import Figure
from typing import Optional, Union

from .base import Layout
from .page import PageElement


class Image(PageElement):
    def __init__(
        self,
        image_url: str,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.image_url = image_url

    def compile(self, layout: Optional[Layout] = None) -> list[dict]:
        if not layout:
            layout = Layout(self).calculate()
        else:
            layout = layout.push(self)

        return [
            {
                "createImage": {
                    "objectId": self.object_id,
                    "url": self.image_url,
                    "elementProperties": self._element_properties(layout),
                }
            }
        ]


def image(
    image_url: str,
    **kwargs,
) -> Image:
    return Image(**{**{"image_url": image_url}, **kwargs})
