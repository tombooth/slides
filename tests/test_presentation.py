from slides.api_types import Dimension, Unit
from slides.presentation import Presentation


def test_width_height():
    pres = Presentation(
        width=Dimension(100, Unit.PT),
        height=Dimension(200, Unit.PT),
    )

    slide = pres.slide()

    assert slide.width == Dimension(100, Unit.PT)
    assert slide.height == Dimension(200, Unit.PT)
