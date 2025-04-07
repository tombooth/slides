from typing import Optional

from .base import Operation, Layout
from .shape import Shape


class InsertText(Operation):
    def __init__(self, text: str, **kwargs):
        super().__init__(**kwargs)
        self.text = text

    def compile(self, layout: Optional[Layout] = None) -> list[dict]:
        if not layout:
            raise ValueError("layout is required for InsertText operation")

        shape = layout.first_parent(Shape)

        return [
            {
                "insertText": {
                    "objectId": shape.object_id,
                    "text": self.text,
                }
            }
        ]


def insert_text(text, **kwargs) -> InsertText:
    return InsertText(**{**{"text": text}, **kwargs})
