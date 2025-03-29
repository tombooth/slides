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
