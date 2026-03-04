import json
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from slides.mcp.tools import create_presentation, create_slides, read_presentation, upload_image
from slides.mcp.models import Element, SlideDefinition


class TestCreatePresentation:
    @pytest.mark.asyncio
    async def test_creates_presentation_with_title(self):
        mock_service = MagicMock()
        mock_service.presentations().create().execute.return_value = {
            "presentationId": "pres-123",
            "pageSize": {
                "width": {"magnitude": 720, "unit": "PT"},
                "height": {"magnitude": 405, "unit": "PT"},
            },
        }

        with patch("slides.mcp.tools._build_slides_service", return_value=mock_service):
            result = await create_presentation(
                title="My Deck",
                credentials=MagicMock(),
            )

        assert result["presentation_id"] == "pres-123"
        assert "url" in result
        assert "docs.google.com" in result["url"]
        mock_service.presentations().create.assert_called()


class TestCreateSlides:
    @pytest.mark.asyncio
    async def test_creates_slides_with_elements(self):
        mock_service = MagicMock()
        mock_service.presentations().get().execute.return_value = {
            "presentationId": "pres-456",
            "pageSize": {
                "width": {"magnitude": 720, "unit": "PT"},
                "height": {"magnitude": 405, "unit": "PT"},
            },
        }
        mock_service.presentations().batchUpdate().execute.return_value = {
            "replies": [{}]
        }

        slides_input = [
            SlideDefinition(
                layout={"flex_direction": "column"},
                children=[
                    Element(type="text_box", text="Hello Slide"),
                ],
            )
        ]

        with patch("slides.mcp.tools._build_slides_service", return_value=mock_service):
            result = await create_slides(
                presentation_id="pres-456",
                slides=slides_input,
                credentials=MagicMock(),
            )

        assert result["slides_created"] == 1
        # Verify batchUpdate was called with requests containing createSlide
        call_args = mock_service.presentations().batchUpdate.call_args
        body = call_args[1]["body"] if "body" in (call_args[1] or {}) else call_args[0][0] if call_args[0] else call_args[1].get("body")
        requests = body["requests"]
        assert any("createSlide" in r for r in requests)
        assert any("createShape" in r for r in requests)

    @pytest.mark.asyncio
    async def test_creates_multiple_slides(self):
        mock_service = MagicMock()
        mock_service.presentations().get().execute.return_value = {
            "presentationId": "pres-789",
            "pageSize": {
                "width": {"magnitude": 720, "unit": "PT"},
                "height": {"magnitude": 405, "unit": "PT"},
            },
        }
        mock_service.presentations().batchUpdate().execute.return_value = {
            "replies": [{}]
        }

        slides_input = [
            SlideDefinition(children=[Element(type="text_box", text="Slide 1")]),
            SlideDefinition(children=[Element(type="text_box", text="Slide 2")]),
        ]

        with patch("slides.mcp.tools._build_slides_service", return_value=mock_service):
            result = await create_slides(
                presentation_id="pres-789",
                slides=slides_input,
                credentials=MagicMock(),
            )

        assert result["slides_created"] == 2


class TestReadPresentation:
    @pytest.mark.asyncio
    async def test_reads_presentation_structure(self):
        mock_service = MagicMock()
        mock_service.presentations().get().execute.return_value = {
            "presentationId": "pres-read",
            "pageSize": {
                "width": {"magnitude": 720, "unit": "PT"},
                "height": {"magnitude": 405, "unit": "PT"},
            },
            "slides": [
                {"objectId": "slide-1"},
                {"objectId": "slide-2"},
            ],
        }

        with patch("slides.mcp.tools._build_slides_service", return_value=mock_service):
            result = await read_presentation(
                presentation_url="https://docs.google.com/presentation/d/pres-read/edit",
                credentials=MagicMock(),
            )

        assert result["presentation_id"] == "pres-read"
        assert result["slide_count"] == 2
        assert result["slide_ids"] == ["slide-1", "slide-2"]
        assert result["width"] == {"magnitude": 720, "unit": "PT"}


class TestUploadImage:
    @pytest.mark.asyncio
    async def test_uploads_and_returns_signed_url(self):
        with patch("slides.mcp.tools.signed_url_for", return_value="https://storage.googleapis.com/signed-url"):
            result = await upload_image(
                file_path="/tmp/test.png",
                bucket="my-bucket",
                credentials=MagicMock(),
            )

        assert result["signed_url"] == "https://storage.googleapis.com/signed-url"
