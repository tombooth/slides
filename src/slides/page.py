from dataclasses import dataclass
from typing import Optional, Union
from pyyoga import YogaNode, FlexDirection, JustifyContent, Align

from .api_types import Dimension, Unit
from .base import Layout
from .object import Object


@dataclass
class BoxDimension:
    left: Optional[Dimension] = None
    top: Optional[Dimension] = None
    right: Optional[Dimension] = None
    bottom: Optional[Dimension] = None

    @staticmethod
    def parse(
        box_dimension: Optional[Union[str, "BoxDimension"]],
    ) -> Optional["BoxDimension"]:
        if box_dimension is None:
            return None

        if isinstance(box_dimension, BoxDimension):
            return box_dimension

        box_dimension = box_dimension.strip().split(" ")

        if len(box_dimension) == 1:
            return BoxDimension(
                left=Dimension.parse(box_dimension[0]),
                top=Dimension.parse(box_dimension[0]),
                right=Dimension.parse(box_dimension[0]),
                bottom=Dimension.parse(box_dimension[0]),
            )

        elif len(box_dimension) == 4:
            return BoxDimension(
                left=Dimension.parse(box_dimension[0]),
                top=Dimension.parse(box_dimension[1]),
                right=Dimension.parse(box_dimension[2]),
                bottom=Dimension.parse(box_dimension[3]),
            )
        else:
            raise ValueError(f"Invalid box dimension format: {box_dimension}")

        return None


@dataclass
class GapDimension:
    row: Optional[Dimension] = None
    column: Optional[Dimension] = None

    @staticmethod
    def parse(
        gap_dimension: Optional[Union[str, "GapDimension"]],
    ) -> Optional["GapDimension"]:
        if gap_dimension is None:
            return None

        if isinstance(gap_dimension, GapDimension):
            return gap_dimension

        gap_dimension = gap_dimension.strip().split(" ")

        if len(gap_dimension) == 1:
            return GapDimension(
                row=Dimension.parse(gap_dimension[0]),
                column=Dimension.parse(gap_dimension[0]),
            )

        elif len(gap_dimension) == 2:
            return GapDimension(
                row=Dimension.parse(gap_dimension[0]),
                column=Dimension.parse(gap_dimension[1]),
            )
        else:
            raise ValueError(f"Invalid box dimension format: {gap_dimension}")

        return None


# i wish slides supported padding, but https://issuetracker.google.com/issues/209837879
class Box(Object):
    width: Optional[Dimension]
    height: Optional[Dimension]
    gap: Optional[GapDimension]
    padding: Optional[BoxDimension]  # slides can't set padding on shapes
    margin: Optional[BoxDimension]
    border: Optional[Dimension]  # slides can't set borders separately
    flex_direction: Optional[FlexDirection]
    justify_content: Optional[JustifyContent]
    align_content: Optional[Align]
    flex_grow: Optional[float]

    def __init__(
        self,
        width: Optional[str | Dimension] = None,
        height: Optional[str | Dimension] = None,
        gap: Optional[str | GapDimension] = None,
        padding: Optional[str | BoxDimension] = None,
        margin: Optional[str | BoxDimension] = None,
        border: Optional[str | Dimension] = None,
        flex_direction: Optional[str | FlexDirection] = None,
        justify_content: Optional[str | JustifyContent] = None,
        align_content: Optional[str | Align] = None,
        flex_grow: Optional[float] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.width = Dimension.parse(width)
        self.height = Dimension.parse(height)
        self.gap = GapDimension.parse(gap)
        self.padding = BoxDimension.parse(padding)
        self.margin = BoxDimension.parse(margin)
        self.border = Dimension.parse(border)
        self.flex_direction = FlexDirection.parse(flex_direction)
        self.justify_content = JustifyContent.parse(justify_content)
        self.align_content = Align.parse(align_content)
        self.flex_grow = flex_grow

        self._node = None

    def node(self) -> Optional[YogaNode]:
        if self._node is not None:
            return self._node

        node = YogaNode()

        if self.width is not None:
            node.set_width(self.width.to_float())
        if self.height is not None:
            node.set_height(self.height.to_float())

        if self.gap is not None:
            if self.gap.row is not None:
                node.set_gap("row", self.gap.row.to_float())
            if self.gap.column is not None:
                node.set_gap("column", self.gap.column.to_float())

        if self.padding is not None:
            if self.padding.left is not None:
                node.set_padding("left", self.padding.left.to_float())
            if self.padding.top is not None:
                node.set_padding("top", self.padding.top.to_float())
            if self.padding.right is not None:
                node.set_padding("right", self.padding.right.to_float())
            if self.padding.bottom is not None:
                node.set_padding("bottom", self.padding.bottom.to_float())

        if self.margin is not None:
            if self.margin.left is not None:
                node.set_margin("left", self.margin.left.to_float())
            if self.margin.top is not None:
                node.set_margin("top", self.margin.top.to_float())
            if self.margin.right is not None:
                node.set_margin("right", self.margin.right.to_float())
            if self.margin.bottom is not None:
                node.set_margin("bottom", self.margin.bottom.to_float())

        if self.border is not None:
            node.set_border("left", self.border.to_float())
            node.set_border("top", self.border.to_float())
            node.set_border("right", self.border.to_float())
            node.set_border("bottom", self.border.to_float())

        if self.flex_direction is not None:
            node.set_flex_direction(self.flex_direction)
        if self.justify_content is not None:
            node.set_justify_content(self.justify_content)
        if self.align_content is not None:
            node.set_align_content(self.align_content)
        if self.flex_grow is not None:
            node.set_flex_grow(self.flex_grow)

        if len(self.children) > 0:
            for child in self.children:
                child_node = child.node()

                if child_node is not None:
                    node.insert_child(child_node, node.get_child_count())

        self._node = node

        return node

    def compile(self, layout: Optional[Layout] = None) -> list[dict]:
        if layout is None:
            layout = Layout(self).calculate()
        else:
            layout = layout.push(self)

        return [
            request
            for child in self.children
            for request in child.compile(layout=layout)
        ]


class Page(Box):
    pass


class PageElement(Box):
    def __init__(
        self,
        **kwargs,
    ):
        super().__init__(**kwargs)

    def _element_properties(self, layout: Layout) -> dict:
        page_object = layout.first_parent(Page)
        (x, y, width, height) = layout.get()

        return {
            "pageObjectId": page_object.object_id,
            "size": {
                "width": Dimension(width, Unit.EMU).to_dict(),
                "height": Dimension(height, Unit.EMU).to_dict(),
            },
            "transform": {
                "scaleX": 1,
                "scaleY": 1,
                "translateX": x,
                "translateY": y,
                "unit": "EMU",
            },
        }


class Slide(Page):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def compile(self, layout: Optional[Layout] = None) -> list[dict]:
        if layout is None:
            layout = Layout(self).calculate()
        else:
            layout = layout.push(self)

        if self._new:
            requests = [{"createSlide": {"objectId": self.object_id}}]
        else:
            requests = [
                {
                    "deleteObject": {
                        "objectId": self.object_id,
                    }
                },
                {"createSlide": {"objectId": self.object_id}},
            ]

        return requests + [
            request
            for child in self.children
            for request in child.compile(layout=layout)
        ]


def box(**kwargs) -> Box:
    return Box(**kwargs)


def slide(**kwargs) -> Slide:
    return Slide(**kwargs)
