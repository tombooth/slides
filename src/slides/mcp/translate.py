from slides.image import image
from slides.operation import insert_text
from slides.page import box
from slides.presentation import Presentation
from slides.shape import text_box

from .models import Element, SlideDefinition


# Props that belong to text_box/shape but not to box
_SHAPE_PROPS = {"alignment", "color", "content_alignment", "background_color", "border_color"}
# Props that belong to box layout
_BOX_PROPS = {
    "width", "height", "flex_direction", "justify_content", "align_content",
    "flex_grow", "gap", "padding", "margin", "border",
}


def build_element(el: Element):
    props = dict(el.props)

    if el.type == "text_box":
        tb = text_box(**props)
        if el.text is not None:
            tb(insert_text(el.text))
        return tb

    elif el.type == "box":
        b = box(**props)
        if el.children:
            b(*[build_element(c) for c in el.children])
        return b

    elif el.type == "image":
        return image(image_url=el.image_url, **props)

    else:
        raise ValueError(f"Unknown element type: {el.type}")


def build_slide(presentation: Presentation, slide_def: SlideDefinition):
    kwargs = dict(slide_def.layout)
    if slide_def.object_id is not None:
        kwargs["object_id"] = slide_def.object_id

    s = presentation.slide(**kwargs)

    if slide_def.children:
        s(*[build_element(c) for c in slide_def.children])

    return s
