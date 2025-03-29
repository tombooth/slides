from dataclasses import dataclass
from enum import Enum


class Unit(Enum):
    UNIT_UNSPECIFIED = "UNIT_UNSPECIFIED"
    EMU = "EMU"
    PT = "PT"


@dataclass
class Dimension:
    magnitude: float
    unit: Unit


class Type(Enum):
    TEXT_BOX = "TEXT_BOX"
