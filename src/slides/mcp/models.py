from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel


class Element(BaseModel):
    type: Literal["box", "text_box", "image"]
    props: dict = {}
    text: Optional[str] = None
    image_url: Optional[str] = None
    children: list[Element] = []


class SlideDefinition(BaseModel):
    layout: dict = {}
    object_id: Optional[str] = None
    children: list[Element] = []
