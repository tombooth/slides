from typing import Optional

from .base import Operation
from .shape import Shape


class InsertText(Operation):
    def __init__(self, text: str, **kwargs):
        super().__init__(**kwargs)
        self.text = text

    def compile(self, context: Optional[list[Operation]] = None) -> list[dict]:
        if not context:
            raise ValueError("Context is required for InsertText operation")

        shape = context.find_first(Shape)

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
