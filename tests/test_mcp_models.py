import pytest
from pydantic import ValidationError

from slides.mcp.models import Element, SlideDefinition


class TestElement:
    def test_text_box_element(self):
        el = Element(type="text_box", text="Hello")
        assert el.type == "text_box"
        assert el.text == "Hello"
        assert el.children == []
        assert el.props == {}

    def test_box_element(self):
        el = Element(type="box", props={"flex_direction": "row"})
        assert el.type == "box"
        assert el.props == {"flex_direction": "row"}

    def test_image_element(self):
        el = Element(type="image", image_url="https://example.com/img.png")
        assert el.type == "image"
        assert el.image_url == "https://example.com/img.png"

    def test_invalid_type_rejected(self):
        with pytest.raises(ValidationError):
            Element(type="invalid")

    def test_recursive_children(self):
        child = Element(type="text_box", text="child")
        parent = Element(type="box", children=[child])
        assert len(parent.children) == 1
        assert parent.children[0].type == "text_box"
        assert parent.children[0].text == "child"

    def test_deeply_nested_children(self):
        inner = Element(type="text_box", text="deep")
        mid = Element(type="box", children=[inner])
        outer = Element(type="box", children=[mid])
        assert outer.children[0].children[0].text == "deep"

    def test_props_with_layout(self):
        el = Element(
            type="text_box",
            text="styled",
            props={
                "flex_grow": 1,
                "alignment": "CENTER",
                "color": "#FF0000",
                "background_color": "#FFFFFF",
            },
        )
        assert el.props["flex_grow"] == 1
        assert el.props["color"] == "#FF0000"

    def test_element_from_dict(self):
        data = {
            "type": "box",
            "props": {"flex_direction": "column"},
            "children": [
                {"type": "text_box", "text": "Hello"},
                {"type": "image", "image_url": "https://example.com/img.png"},
            ],
        }
        el = Element.model_validate(data)
        assert el.type == "box"
        assert len(el.children) == 2
        assert el.children[0].type == "text_box"
        assert el.children[1].type == "image"


class TestSlideDefinition:
    def test_basic_slide(self):
        sd = SlideDefinition(children=[Element(type="text_box", text="Title")])
        assert len(sd.children) == 1
        assert sd.layout == {}
        assert sd.object_id is None

    def test_slide_with_layout(self):
        sd = SlideDefinition(
            layout={"flex_direction": "column", "justify_content": "center"},
            children=[],
        )
        assert sd.layout["flex_direction"] == "column"

    def test_slide_with_object_id(self):
        sd = SlideDefinition(object_id="existing-slide-id", children=[])
        assert sd.object_id == "existing-slide-id"

    def test_slide_from_dict(self):
        data = {
            "layout": {"flex_direction": "row"},
            "object_id": "slide-1",
            "children": [
                {
                    "type": "box",
                    "props": {"flex_direction": "column"},
                    "children": [
                        {"type": "text_box", "text": "Hello"},
                    ],
                }
            ],
        }
        sd = SlideDefinition.model_validate(data)
        assert sd.object_id == "slide-1"
        assert sd.children[0].children[0].text == "Hello"


class TestSchemaExamples:
    def test_element_schema_has_examples(self):
        schema = Element.model_json_schema()
        # Element is self-referential, so schema uses $defs/Element with a $ref
        element_schema = schema.get("$defs", {}).get("Element", schema)
        assert "examples" in element_schema
        assert len(element_schema["examples"]) >= 1

    def test_slide_definition_schema_has_examples(self):
        schema = SlideDefinition.model_json_schema()
        assert "examples" in schema
        assert len(schema["examples"]) >= 1
