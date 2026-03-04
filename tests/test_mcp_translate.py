from slides.mcp.models import Element, SlideDefinition
from slides.mcp.translate import build_element, build_slide
from slides.presentation import Presentation
from slides.api_types import Dimension, Unit


class TestBuildElementTextBox:
    def test_text_box_creates_shape_and_inserts_text(self):
        el = Element(type="text_box", text="Hello world!")
        slide_def = SlideDefinition(children=[el])
        pres = Presentation(
            id="test", width=Dimension(720, Unit.PT), height=Dimension(405, Unit.PT)
        )
        slide_obj = build_slide(pres, slide_def)
        requests = slide_obj.compile()

        assert any("createSlide" in r for r in requests)
        assert any("createShape" in r for r in requests)
        assert any(
            "insertText" in r and r["insertText"]["text"] == "Hello world!"
            for r in requests
        )

    def test_text_box_with_style_props(self):
        el = Element(
            type="text_box",
            text="Styled",
            props={"alignment": "CENTER", "color": "#FF0000"},
        )
        slide_def = SlideDefinition(children=[el])
        pres = Presentation(
            id="test", width=Dimension(720, Unit.PT), height=Dimension(405, Unit.PT)
        )
        slide_obj = build_slide(pres, slide_def)
        requests = slide_obj.compile()

        assert any("updateTextStyle" in r for r in requests)
        assert any("updateParagraphStyle" in r for r in requests)


class TestBuildElementBox:
    def test_box_with_children(self):
        el = Element(
            type="box",
            props={"flex_direction": "row"},
            children=[
                Element(type="text_box", text="Left"),
                Element(type="text_box", text="Right"),
            ],
        )
        slide_def = SlideDefinition(children=[el])
        pres = Presentation(
            id="test", width=Dimension(720, Unit.PT), height=Dimension(405, Unit.PT)
        )
        slide_obj = build_slide(pres, slide_def)
        requests = slide_obj.compile()

        assert any("createSlide" in r for r in requests)
        # Two text boxes should produce two createShape requests
        create_shapes = [r for r in requests if "createShape" in r]
        assert len(create_shapes) == 2
        # And two insertText requests
        insert_texts = [r for r in requests if "insertText" in r]
        assert len(insert_texts) == 2
        texts = {r["insertText"]["text"] for r in insert_texts}
        assert texts == {"Left", "Right"}


class TestBuildElementImage:
    def test_image_element(self):
        el = Element(
            type="image",
            image_url="https://example.com/pic.png",
            props={"width": "200pt", "height": "150pt"},
        )
        slide_def = SlideDefinition(children=[el])
        pres = Presentation(
            id="test", width=Dimension(720, Unit.PT), height=Dimension(405, Unit.PT)
        )
        slide_obj = build_slide(pres, slide_def)
        requests = slide_obj.compile()

        assert any(
            "createImage" in r
            and r["createImage"]["url"] == "https://example.com/pic.png"
            for r in requests
        )


class TestBuildSlide:
    def test_slide_with_layout_props(self):
        slide_def = SlideDefinition(
            layout={"flex_direction": "column", "justify_content": "center"},
            children=[Element(type="text_box", text="Centered")],
        )
        pres = Presentation(
            id="test", width=Dimension(720, Unit.PT), height=Dimension(405, Unit.PT)
        )
        slide_obj = build_slide(pres, slide_def)
        requests = slide_obj.compile()

        assert any("createSlide" in r for r in requests)
        assert any("createShape" in r for r in requests)

    def test_slide_with_object_id_produces_delete_then_create(self):
        slide_def = SlideDefinition(
            object_id="existing-slide",
            children=[Element(type="text_box", text="Updated")],
        )
        pres = Presentation(
            id="test", width=Dimension(720, Unit.PT), height=Dimension(405, Unit.PT)
        )
        slide_obj = build_slide(pres, slide_def)
        requests = slide_obj.compile()

        assert any(
            "deleteObject" in r and r["deleteObject"]["objectId"] == "existing-slide"
            for r in requests
        )
        assert any(
            "createSlide" in r and r["createSlide"]["objectId"] == "existing-slide"
            for r in requests
        )

    def test_full_nested_slide(self):
        """Title + two-column body layout."""
        slide_def = SlideDefinition(
            layout={"flex_direction": "column"},
            children=[
                Element(
                    type="text_box",
                    text="Title Slide",
                    props={"alignment": "CENTER", "content_alignment": "MIDDLE"},
                ),
                Element(
                    type="box",
                    props={"flex_direction": "row", "flex_grow": 1},
                    children=[
                        Element(type="text_box", text="Column 1", props={"flex_grow": 1}),
                        Element(type="text_box", text="Column 2", props={"flex_grow": 1}),
                    ],
                ),
            ],
        )
        pres = Presentation(
            id="test", width=Dimension(720, Unit.PT), height=Dimension(405, Unit.PT)
        )
        slide_obj = build_slide(pres, slide_def)
        requests = slide_obj.compile()

        # 1 createSlide + 3 createShape (title + 2 columns)
        assert sum(1 for r in requests if "createSlide" in r) == 1
        assert sum(1 for r in requests if "createShape" in r) == 3
        # Check that our actual text content appears in insertText requests
        # (styled text_boxes also produce a "[holding]" insertText for style application)
        user_texts = {
            r["insertText"]["text"]
            for r in requests
            if "insertText" in r and r["insertText"]["text"] != "[holding]"
        }
        assert user_texts == {"Title Slide", "Column 1", "Column 2"}
