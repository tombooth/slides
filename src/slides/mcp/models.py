from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict


class Element(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "type": "text_box",
                    "text": "Hello World",
                    "props": {
                        "flex_grow": 1,
                        "color": "#FFFFFF",
                        "font_size": 24,
                        "alignment": "CENTER",
                        "content_alignment": "MIDDLE",
                        "background_color": "#4285F4",
                    },
                },
                {
                    "type": "box",
                    "props": {
                        "flex_direction": "row",
                        "justify_content": "space_between",
                        "align_items": "center",
                        "gap": 20,
                        "padding": 30,
                    },
                    "children": [
                        {"type": "text_box", "text": "Left", "props": {"flex_grow": 1}},
                        {"type": "text_box", "text": "Right", "props": {"flex_grow": 1}},
                    ],
                },
                {
                    "type": "image",
                    "image_url": "https://example.com/photo.png",
                    "props": {"width": 300, "height": 200},
                },
            ]
        }
    )

    type: Literal["box", "text_box", "image"]
    props: dict = {}
    text: Optional[str] = None
    image_url: Optional[str] = None
    children: list[Element] = []


class SlideDefinition(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "layout": {
                        "flex_direction": "column",
                        "justify_content": "center",
                        "align_items": "center",
                        "padding": 40,
                        "background_color": "#1A1A2E",
                    },
                    "children": [
                        {
                            "type": "text_box",
                            "text": "Presentation Title",
                            "props": {
                                "color": "#FFFFFF",
                                "font_size": 40,
                                "bold": True,
                                "alignment": "CENTER",
                            },
                        },
                        {
                            "type": "text_box",
                            "text": "Subtitle goes here",
                            "props": {
                                "color": "#CCCCCC",
                                "font_size": 20,
                                "alignment": "CENTER",
                                "margin": {"top": 10},
                            },
                        },
                    ],
                }
            ]
        }
    )

    layout: dict = {}
    object_id: Optional[str] = None
    children: list[Element] = []
