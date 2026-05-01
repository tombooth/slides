import json

from slides.page import slide, box
from slides.shape import text_box
from slides.operation import insert_text


def test_children():
    text_box_1 = text_box()(insert_text("Hello world!"))
    slide_1 = slide()(text_box_1)

    requests = slide_1.compile()

    assert any("createSlide" in request for request in requests)
    assert any(
        "createShape" in request
        and request["createShape"]["objectId"] == text_box_1.object_id
        for request in requests
    )
    assert any(
        "insertText" in request
        and request["insertText"]["objectId"] == text_box_1.object_id
        for request in requests
    )


def test_layout():
    slide_1 = slide(
        width="720pt",
        height="405pt",
        flex_direction="column",
        justify_content="space-around",
        align_content="center",
    )(
        text_box(
            flex_grow=1,
            alignment="center",
            content_alignment="middle",
        )(insert_text("I'm in the middle")),
    )

    requests = slide_1.compile()

    assert any(
        "createShape" in request
        and request["createShape"]["elementProperties"]["size"]["width"]["magnitude"]
        == slide_1.width.to_float()
        and request["createShape"]["elementProperties"]["size"]["height"]["magnitude"]
        == slide_1.height.to_float()
        and request["createShape"]["elementProperties"]["transform"]["translateX"] == 0
        and request["createShape"]["elementProperties"]["transform"]["translateY"] == 0
        for request in requests
    )


def _find_update_text_style(requests, object_id):
    for r in requests:
        if "updateTextStyle" in r and r["updateTextStyle"]["objectId"] == object_id:
            return r["updateTextStyle"]
    return None


def test_font_properties_on_text_box():
    tb = text_box(font_family="Roboto", font_size="18pt", font_weight=700)(
        insert_text("hi")
    )
    slide_1 = slide()(tb)

    requests = slide_1.compile()
    update = _find_update_text_style(requests, tb.object_id)

    assert update is not None
    assert update["style"]["fontFamily"] == "Roboto"
    assert update["style"]["fontSize"]["magnitude"] == 18
    assert update["style"]["weightedFontFamily"]["fontFamily"] == "Roboto"
    assert update["style"]["weightedFontFamily"]["weight"] == 700
    fields = set(update["fields"].split(","))
    assert {"fontFamily", "fontSize", "weightedFontFamily"} <= fields


def test_font_properties_cascade_from_parent_box():
    tb = text_box()(insert_text("hi"))
    slide_1 = slide(font_family="Inter", font_size="12pt")(box()(tb))

    requests = slide_1.compile()
    update = _find_update_text_style(requests, tb.object_id)

    assert update is not None
    assert update["style"]["fontFamily"] == "Inter"
    assert update["style"]["fontSize"]["magnitude"] == 12


def test_font_properties_child_overrides_parent():
    tb = text_box(font_size="24pt")(insert_text("hi"))
    slide_1 = slide(font_family="Inter", font_size="12pt")(tb)

    requests = slide_1.compile()
    update = _find_update_text_style(requests, tb.object_id)

    assert update["style"]["fontFamily"] == "Inter"
    assert update["style"]["fontSize"]["magnitude"] == 24


def test_color_cascades_from_parent_box():
    tb = text_box()(insert_text("hi"))
    slide_1 = slide(color="#ff0000")(box()(tb))

    requests = slide_1.compile()
    update = _find_update_text_style(requests, tb.object_id)

    assert update is not None
    fg = update["style"]["foregroundColor"]["opaqueColor"]["rgbColor"]
    assert fg["red"] == 1.0
    assert fg["green"] == 0.0
    assert fg["blue"] == 0.0
