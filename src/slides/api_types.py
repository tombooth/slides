import re

from dataclasses import dataclass
from enum import Enum
from typing import Union, Optional


class Unit(str, Enum):
    UNIT_UNSPECIFIED = "UNIT_UNSPECIFIED"
    EMU = "EMU"
    PT = "PT"


@dataclass
class Dimension:
    magnitude: float
    unit: Unit

    @staticmethod
    def parse(dimension: Optional[Union[str, "Dimension"]]) -> Optional["Dimension"]:
        if dimension is None:
            return None

        if isinstance(dimension, Dimension):
            return dimension

        if isinstance(dimension, str) and dimension.lower() == "none":
            return None

        try:
            # uses a regex to split the number and the unit
            # e.g. "10pt" -> (10, "pt")
            # e.g. "10 pt" -> (10, "pt")
            match = re.match(r"^(\d+(\.\d+)?)\s*([a-zA-Z]+)$", dimension)
            if not match:
                raise ValueError(f"Invalid dimension format: {dimension}")
            magnitude = match.group(1)
            unit = match.group(3).upper()

            if unit not in Unit.__members__:
                raise ValueError(f"Invalid unit: {unit}")

            return Dimension(float(magnitude), Unit[unit])
        except ValueError:
            raise ValueError(f"Invalid dimension format: {dimension}")

    def to_dict(self) -> dict:
        return {
            "magnitude": self.magnitude,
            "unit": self.unit,
        }

    def to_float(self) -> float:
        if self.unit == Unit.PT:  # convert to emu
            return self.magnitude * 12_700
        elif self.unit == Unit.EMU:
            return self.magnitude
        else:
            raise ValueError(f"Unsupported unit: {self.unit}")


class Type(str, Enum):
    TEXT_BOX = "TEXT_BOX"


class ContentAlignment(str, Enum):
    CONTENT_ALIGNMENT_UNSPECIFIED = "CONTENT_ALIGNMENT_UNSPECIFIED"
    TOP = "TOP"
    MIDDLE = "MIDDLE"
    BOTTOM = "BOTTOM"

    @staticmethod
    def parse(
        content_alignment: Optional[Union[str, "ContentAlignment"]],
    ) -> Optional["ContentAlignment"]:
        if content_alignment is None:
            return None

        if isinstance(content_alignment, ContentAlignment):
            return content_alignment

        content_alignment = content_alignment.upper()

        if content_alignment == "TOP":
            return ContentAlignment.TOP
        elif content_alignment == "MIDDLE":
            return ContentAlignment.MIDDLE
        elif content_alignment == "BOTTOM":
            return ContentAlignment.BOTTOM
        else:
            raise ValueError(
                f"Invalid content alignment: {content_alignment} not in [top, middle, bottom]"
            )


class Alignment(str, Enum):
    ALIGNMENT_UNSPECIFIED = "ALIGNMENT_UNSPECIFIED"
    START = "START"
    CENTER = "CENTER"
    END = "END"
    JUSTIFIED = "JUSTIFIED"

    @staticmethod
    def parse(alignment: Optional[Union[str, "Alignment"]]) -> Optional["Alignment"]:
        if alignment is None:
            return None

        if isinstance(alignment, Alignment):
            return alignment

        alignment = alignment.upper()

        if alignment == "START":
            return Alignment.START
        elif alignment == "CENTER":
            return Alignment.CENTER
        elif alignment == "END":
            return Alignment.END
        elif alignment == "JUSTIFIED":
            return Alignment.JUSTIFIED
        else:
            raise ValueError(
                f"Invalid alignment: {alignment} not in [start, center, end, justified]"
            )


class ThemeColorType(str, Enum):
    THEME_COLOR_TYPE_UNSPECIFIED = "THEME_COLOR_TYPE_UNSPECIFIED"
    DARK1 = "DARK1"
    LIGHT1 = "LIGHT1"
    DARK2 = "DARK2"
    LIGHT2 = "LIGHT2"
    ACCENT1 = "ACCENT1"
    ACCENT2 = "ACCENT2"
    ACCENT3 = "ACCENT3"
    ACCENT4 = "ACCENT4"
    ACCENT5 = "ACCENT5"
    ACCENT6 = "ACCENT6"
    HYPERLINK = "HYPERLINK"
    FOLLOWED_HYPERLINK = "FOLLOWED_HYPERLINK"
    TEXT1 = "TEXT1"
    BACKGROUND1 = "BACKGROUND1"
    TEXT2 = "TEXT2"
    BACKGROUND2 = "BACKGROUND2"

    @staticmethod
    def parse(
        theme_color_type: Optional[Union[str, "ThemeColorType"]],
    ) -> Optional["ThemeColorType"]:
        if theme_color_type is None:
            return None

        if isinstance(theme_color_type, ThemeColorType):
            return theme_color_type

        theme_color_type = theme_color_type.upper()

        if theme_color_type in ThemeColorType.__members__:
            return ThemeColorType[theme_color_type]
        else:
            raise ValueError(f"Invalid theme color type: {theme_color_type}")


@dataclass
class RGBColor:
    red: float
    green: float
    blue: float

    @staticmethod
    def parse(color: Optional[Union[str, "RGBColor"]]) -> Optional["RGBColor"]:
        if color is None:
            return None

        if isinstance(color, RGBColor):
            return color

        if isinstance(color, str):
            # parse css # color format
            if color.startswith("#"):
                color = color.lstrip("#")
                if len(color) == 6:
                    r = int(color[0:2], 16)
                    g = int(color[2:4], 16)
                    b = int(color[4:6], 16)
                    return RGBColor(r / 255, g / 255, b / 255)
                if len(color) == 3:
                    r = int(color[0:1], 16)
                    g = int(color[1:2], 16)
                    b = int(color[2:3], 16)
                    return RGBColor(r / 15, g / 15, b / 15)
                else:
                    raise ValueError(f"Invalid hex color format: {color}")

        raise ValueError(f"Invalid RGB color format: {color}")

    def to_dict(self) -> dict:
        return {
            "red": self.red,
            "green": self.green,
            "blue": self.blue,
        }


@dataclass
class OpaqueColor:
    rgbColor: Optional[RGBColor] = None
    themeColor: Optional[ThemeColorType] = None

    @staticmethod
    def parse(color: Optional[Union[str, "OpaqueColor"]]) -> Optional["OpaqueColor"]:
        if color is None:
            return None

        if isinstance(color, OpaqueColor):
            return color

        if isinstance(color, str):
            # parse css # color format
            if color.startswith("#"):
                return OpaqueColor(rgbColor=RGBColor.parse(color))
            else:
                return OpaqueColor(themeColor=ThemeColorType.parse(color))

        raise ValueError(f"Invalid opaque color format: {color}")

    def to_dict(self) -> dict:
        if self.rgbColor:
            return {"rgbColor": self.rgbColor.to_dict()}
        elif self.themeColor:
            return {"themeColor": self.themeColor}
        else:
            raise ValueError("No color specified")
