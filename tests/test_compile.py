import json

from slides.page import slide
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
