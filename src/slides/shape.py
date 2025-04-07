from collections import defaultdict
from typing import Optional

from .api_types import Type, ContentAlignment, Alignment, OpaqueColor
from .base import Layout
from .page import PageElement


class Shape(PageElement):
    type: Type

    def __init__(
        self,
        type: Type,
        content_alignment: Optional[str | ContentAlignment] = None,
        background_color: Optional[str | OpaqueColor] = None,
        border_color: Optional[str | OpaqueColor] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.type = type
        self.content_alignment = ContentAlignment.parse(content_alignment)
        self.background_color = OpaqueColor.parse(background_color)
        self.border_color = OpaqueColor.parse(border_color)

    def _style_shape(self, _: Optional[Layout] = None) -> list[dict]:
        shapeProperties = defaultdict(dict)

        if self.content_alignment:
            shapeProperties["contentAlignment"] = self.content_alignment

        if self.border:
            shapeProperties["outline"]["weight"] = self.border.to_dict()

        if self.border_color:
            shapeProperties["outline"]["outlineFill"] = {
                "solidFill": {"color": self.border_color.to_dict()},
            }

        if self.background_color:
            shapeProperties["shapeBackgroundFill"] = {
                "propertyState": "RENDERED",
                "solidFill": {"color": self.background_color.to_dict()},
            }

        fields = ",".join(shapeProperties.keys())

        if len(shapeProperties) == 0:
            return []
        else:
            return [
                {
                    "updateShapeProperties": {
                        "objectId": self.object_id,
                        "fields": fields,
                        "shapeProperties": shapeProperties,
                    }
                }
            ]

    def compile(self, layout: Optional[Layout] = None) -> list[dict]:
        if layout is None:
            layout = Layout(self).calculate()
        else:
            layout = layout.push(self)

        if self._new:
            requests = [
                {
                    "createShape": {
                        "objectId": self.object_id,
                        "shapeType": self.type,
                        "elementProperties": self._element_properties(layout),
                    },
                },
            ]
        else:
            requests = []

        requests += self._style_shape(layout)

        return requests + [
            request
            for child in self.children
            for request in child.compile(layout=layout)
        ]


class TextBox(Shape):
    def __init__(
        self,
        alignment: Optional[str | Alignment] = None,
        color: Optional[str | OpaqueColor] = None,
        **kwargs,
    ):
        kwargs["type"] = Type.TEXT_BOX
        super().__init__(**kwargs)
        self.alignment = Alignment.parse(alignment)
        self.color = OpaqueColor.parse(color)

    def _style_shape(self, layout: Optional[Layout] = None) -> list[dict]:
        requests = super()._style_shape(layout)

        style_requests = []
        paragraph_style = {}

        if self.alignment:
            paragraph_style["alignment"] = self.alignment

        paragraph_fields = ",".join(paragraph_style.keys())

        if len(paragraph_style) > 0:
            style_requests += [
                {
                    "updateParagraphStyle": {
                        "objectId": self.object_id,
                        "textRange": {"type": "ALL"},
                        "fields": paragraph_fields,
                        "style": paragraph_style,
                    }
                }
            ]

        text_style = {}

        if self.color:
            text_style["foregroundColor"] = {
                "opaqueColor": self.color.to_dict(),
            }

        text_fields = ",".join(text_style.keys())

        if len(text_style) > 0:
            style_requests += [
                {
                    "updateTextStyle": {
                        "objectId": self.object_id,
                        "textRange": {"type": "ALL"},
                        "fields": text_fields,
                        "style": text_style,
                    }
                }
            ]

        if len(style_requests) > 0:
            # there has to be text before we can set the alignment
            requests += (
                [
                    {
                        "insertText": {
                            "objectId": self.object_id,
                            "text": "[holding]",
                        }
                    },
                ]
                + style_requests
                + [
                    {
                        "deleteText": {
                            "objectId": self.object_id,
                            "textRange": {"type": "ALL"},
                        }
                    },
                ]
            )

        return requests


def text_box(**kwargs) -> TextBox:
    return TextBox(**kwargs)
