from slides.page import Slide


def test_create():
    slide = Slide()

    requests = slide.compile()

    assert any("createSlide" in request for request in requests)
    assert not any("deleteObject" in request for request in requests)


def test_update():
    object_id = "wibble"
    slide = Slide(object_id=object_id)

    requests = slide.compile()

    assert any(
        "createSlide" in request and request["createSlide"]["objectId"] == object_id
        for request in requests
    )
    assert any(
        "deleteObject" in request and request["deleteObject"]["objectId"] == object_id
        for request in requests
    )
