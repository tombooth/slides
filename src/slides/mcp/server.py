import os
import urllib.parse

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions, RevocationOptions
from starlette.requests import Request
from starlette.responses import RedirectResponse

from .auth_provider import GoogleOAuthProvider
from .models import SlideDefinition
from .tools import create_presentation, create_slides, read_presentation, upload_image


def create_server() -> FastMCP:
    google_client_id = os.environ["GOOGLE_CLIENT_ID"]
    google_client_secret = os.environ["GOOGLE_CLIENT_SECRET"]
    server_url = os.environ.get("MCP_SERVER_URL", "http://localhost:8000")

    provider = GoogleOAuthProvider(
        google_client_id=google_client_id,
        google_client_secret=google_client_secret,
        server_url=server_url,
    )

    mcp = FastMCP(
        "google-slides",
        instructions="Create and edit Google Slides presentations using flexbox layout.",
        auth_server_provider=provider,
        auth=AuthSettings(
            issuer_url=server_url,
            client_registration_options=ClientRegistrationOptions(
                enabled=True,
                valid_scopes=["presentations"],
                default_scopes=["presentations"],
            ),
            revocation_options=RevocationOptions(enabled=True),
        ),
    )

    # --- Tools ---

    @mcp.tool()
    async def tool_create_presentation(title: str) -> dict:
        """Create a new blank Google Slides presentation.

        Args:
            title: The title for the new presentation.
        Returns:
            JSON with presentation_id, url, and dimensions.
        """
        token = _get_access_token()
        creds = provider.get_google_credentials(token)
        return await create_presentation(title=title, credentials=creds)

    @mcp.tool()
    async def tool_create_slides(
        presentation_id: str, slides: list[SlideDefinition]
    ) -> dict:
        """Create one or more slides in an existing presentation using flexbox layout.

        Args:
            presentation_id: The ID of the target presentation.
            slides: List of slide definitions with layout props and children elements.
                Each element has: type ("box"|"text_box"|"image"), props (layout/style), text, image_url, children.
                Layout props: flex_direction, justify_content, align_content, flex_grow, gap, padding, margin, border, width, height.
                Style props: background_color (#hex), border_color (#hex), color (#hex), alignment (START/CENTER/END/JUSTIFIED), content_alignment (TOP/MIDDLE/BOTTOM).
        Returns:
            JSON with slides_created count, presentation_id, and url.
        """
        token = _get_access_token()
        creds = provider.get_google_credentials(token)
        return await create_slides(
            presentation_id=presentation_id, slides=slides, credentials=creds
        )

    @mcp.tool()
    async def tool_read_presentation(presentation_url: str) -> dict:
        """Read the structure of an existing Google Slides presentation.

        Args:
            presentation_url: The full URL of the Google Slides presentation.
        Returns:
            JSON with presentation_id, dimensions, slide_count, and slide_ids.
        """
        token = _get_access_token()
        creds = provider.get_google_credentials(token)
        return await read_presentation(
            presentation_url=presentation_url, credentials=creds
        )

    # Conditionally register upload_image if GCS bucket is configured
    gcs_bucket = os.environ.get("SLIDES_GCS_BUCKET")
    if gcs_bucket:
        from google.auth import default as google_default

        gcs_credentials, _ = google_default()

        @mcp.tool()
        async def tool_upload_image(file_path: str) -> dict:
            """Upload an image to cloud storage for use in slides.

            Args:
                file_path: Local file path of the image to upload.
            Returns:
                JSON with signed_url (15-min expiry) for use in create_slides image elements.
            """
            return await upload_image(
                file_path=file_path,
                bucket=gcs_bucket,
                credentials=gcs_credentials,
            )

    # --- Google OAuth callback route ---

    app = mcp._mcp_server.app if hasattr(mcp._mcp_server, "app") else None

    def _get_access_token() -> str:
        """Extract access token from the current request context.
        This is a placeholder — in production, FastMCP middleware provides this."""
        # The MCP SDK handles token extraction; tools receive authenticated context
        # For now this returns from request context set by auth middleware
        raise NotImplementedError(
            "Access token extraction depends on MCP SDK request context"
        )

    return mcp
