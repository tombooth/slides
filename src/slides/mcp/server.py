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

INSTRUCTIONS = """\
Google Slides MCP server — create presentations with a flexbox-style layout engine.

WORKFLOW:
1. tool_create_presentation(title) → returns presentation_id
2. tool_create_slides(presentation_id, slides=[...]) → adds slides (batch multiple slides in one call)
3. tool_read_presentation(presentation_url) → inspect an existing presentation

MENTAL MODEL:
- Each slide is a flexbox container (layout props control direction, alignment, gaps).
- Three element types: text_box (text content), box (container for children), image (image_url).
- Props fall into two categories:
  * Layout: flex_direction, justify_content, align_items, flex_grow, gap, padding, margin, width, height
  * Style: background_color, border_color, color, font_size, bold, italic, alignment, content_alignment

TIPS:
- Batch slides: pass multiple SlideDefinition objects in one tool_create_slides call.
- Use flex_grow to fill available space instead of fixed widths.
- Nest box elements to create complex multi-column/row layouts.
- Read slides://reference/props, slides://reference/examples, and slides://reference/colors for detailed references.
"""


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
        instructions=INSTRUCTIONS,
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
        """Create one or more slides in a presentation using flexbox layout.

ELEMENT TYPES:
  text_box — text content (set .text); supports style props
  box      — invisible container for child elements; set flex_direction to lay out children
  image    — displays an image (set .image_url to a public or signed URL)

BOX / LAYOUT PROPS (on slide layout OR any element props):
  flex_direction    : "row" | "column" (default "column")
  justify_content   : "start" | "center" | "end" | "space_between" | "space_around" | "space_evenly"
  align_items       : "start" | "center" | "end" | "stretch"
  flex_grow         : number (0 = fixed size, 1+ = fill proportionally)
  gap               : number in points
  padding           : number or {"top": n, "bottom": n, "left": n, "right": n}
  margin            : number or {"top": n, "bottom": n, "left": n, "right": n}
  width / height    : number in points (prefer flex_grow over fixed sizes)

STYLE PROPS (text_box and box):
  background_color  : hex string, e.g. "#4285F4", or theme name like "ACCENT1"
  border_color      : hex string
  color             : text color, hex string
  font_size         : number in points
  font_family       : string, e.g. "Roboto"
  bold / italic     : boolean
  alignment         : "START" | "CENTER" | "END" | "JUSTIFIED" (horizontal text alignment)
  content_alignment : "TOP" | "MIDDLE" | "BOTTOM" (vertical text alignment)

THEME COLORS: ACCENT1..ACCENT6, TEXT1, TEXT2, BACKGROUND1, BACKGROUND2, HYPERLINK

EXAMPLE — title slide with two columns:
  {"layout": {"flex_direction": "column", "padding": 40, "background_color": "#1A1A2E"},
   "children": [
     {"type": "text_box", "text": "Title", "props": {"color": "#FFF", "font_size": 36, "bold": true, "alignment": "CENTER"}},
     {"type": "box", "props": {"flex_direction": "row", "gap": 20, "flex_grow": 1, "margin": {"top": 20}},
      "children": [
        {"type": "text_box", "text": "Left column content", "props": {"flex_grow": 1, "background_color": "#16213E", "color": "#EEE", "padding": 20}},
        {"type": "text_box", "text": "Right column content", "props": {"flex_grow": 1, "background_color": "#16213E", "color": "#EEE", "padding": 20}}
      ]}
   ]}

TIPS:
- Batch slides: pass multiple SlideDefinition objects in one call.
- Use flex_grow: 1 on children for equal-width columns instead of fixed widths.
- Nest box elements for complex layouts (rows inside columns, etc.).
- Wrap text in text_box; use box only as a structural container.

        Args:
            presentation_id: The ID of the target presentation.
            slides: List of slide definitions with layout props and children elements.
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

    # --- Prompts ---

    @mcp.prompt()
    def create_deck(topic: str) -> str:
        """Step-by-step guide for creating a slide deck on any topic."""
        return f"""\
Create a Google Slides presentation about: {topic}

Follow these steps:
1. Call tool_create_presentation with a clear title.
2. Design 5-8 slides. For each slide, build a SlideDefinition JSON with layout props and children.
3. Call tool_create_slides ONCE with all slides in a single batch.

Slide design guidelines:
- Every slide needs layout props (flex_direction, padding, etc.) and children elements.
- Use consistent colors across slides (pick 2-3 main colors).
- Use font_size 32-40 for titles, 18-24 for body text.
- Add padding (30-50) to all slides for breathing room.

Example slides:

Title slide:
{{"layout": {{"flex_direction": "column", "justify_content": "center", "align_items": "center", "padding": 50, "background_color": "#1A1A2E"}},
 "children": [
   {{"type": "text_box", "text": "Presentation Title", "props": {{"color": "#FFFFFF", "font_size": 40, "bold": true, "alignment": "CENTER"}}}},
   {{"type": "text_box", "text": "Subtitle or author", "props": {{"color": "#CCCCCC", "font_size": 20, "alignment": "CENTER", "margin": {{"top": 10}}}}}}
 ]}}

Content slide:
{{"layout": {{"flex_direction": "column", "padding": 40, "background_color": "#FFFFFF"}},
 "children": [
   {{"type": "text_box", "text": "Slide Title", "props": {{"color": "#1A1A2E", "font_size": 32, "bold": true}}}},
   {{"type": "text_box", "text": "Body text with key points and details.", "props": {{"color": "#333333", "font_size": 18, "flex_grow": 1, "margin": {{"top": 15}}}}}}
 ]}}

Two-column slide:
{{"layout": {{"flex_direction": "column", "padding": 40, "background_color": "#FFFFFF"}},
 "children": [
   {{"type": "text_box", "text": "Comparison", "props": {{"color": "#1A1A2E", "font_size": 32, "bold": true}}}},
   {{"type": "box", "props": {{"flex_direction": "row", "gap": 20, "flex_grow": 1, "margin": {{"top": 15}}}},
    "children": [
      {{"type": "text_box", "text": "Left column", "props": {{"flex_grow": 1, "background_color": "#F0F0F0", "padding": 20, "color": "#333333", "font_size": 16}}}},
      {{"type": "text_box", "text": "Right column", "props": {{"flex_grow": 1, "background_color": "#F0F0F0", "padding": 20, "color": "#333333", "font_size": 16}}}}
    ]}}
 ]}}
"""

    @mcp.prompt()
    def slide_layouts() -> str:
        """Reference of common slide layout patterns."""
        return """\
COMMON SLIDE LAYOUT PATTERNS

1. CENTERED TITLE
   layout: {flex_direction: "column", justify_content: "center", align_items: "center", padding: 50}
   children: [text_box(title, font_size 40, bold), text_box(subtitle, font_size 20)]

2. TITLE + BODY
   layout: {flex_direction: "column", padding: 40}
   children: [text_box(title, font_size 32, bold), text_box(body, flex_grow 1, font_size 18)]

3. TWO COLUMNS
   layout: {flex_direction: "column", padding: 40}
   children: [text_box(title), box(flex_direction: "row", gap: 20, flex_grow: 1,
     children: [text_box(left, flex_grow 1), text_box(right, flex_grow 1)])]

4. THREE COLUMNS
   layout: {flex_direction: "column", padding: 40}
   children: [text_box(title), box(flex_direction: "row", gap: 15, flex_grow: 1,
     children: [text_box(col1, flex_grow 1), text_box(col2, flex_grow 1), text_box(col3, flex_grow 1)])]

5. IMAGE + TEXT
   layout: {flex_direction: "row", padding: 30, gap: 30}
   children: [image(url, width 350), box(flex_direction: "column", flex_grow: 1,
     children: [text_box(title, bold), text_box(description, flex_grow 1)])]

6. BANNER + CONTENT
   layout: {flex_direction: "column", padding: 0}
   children: [box(background_color, padding: 30, children: [text_box(title, color: "#FFF")]),
              box(flex_grow: 1, padding: 30, children: [text_box(body)])]

KEY PRINCIPLES:
- Use flex_direction "column" for vertical stacking (default), "row" for side-by-side.
- Use flex_grow: 1 on elements to fill remaining space.
- Use gap for spacing between siblings, padding for internal spacing, margin for external.
- Wrap columns in a box with flex_direction "row".
"""

    # --- Resources ---

    @mcp.resource("slides://reference/props")
    def resource_props() -> str:
        """Complete property reference for slide layout and element styling."""
        return """\
SLIDES PROPERTY REFERENCE

BOX / LAYOUT PROPS (used in slide layout dict and element props):
  Property          | Type                | Values / Notes
  ------------------|---------------------|--------------------------------------------
  flex_direction    | string              | "row", "column" (default: "column")
  justify_content   | string              | "start", "center", "end", "space_between", "space_around", "space_evenly"
  align_items       | string              | "start", "center", "end", "stretch"
  flex_grow         | number              | 0 = fixed size, 1+ = fill proportionally
  gap               | number              | Space between children (points)
  padding           | number or object    | Uniform: 20, Per-side: {"top": 10, "bottom": 10, "left": 20, "right": 20}
  margin            | number or object    | Same format as padding
  width             | number              | Fixed width in points (prefer flex_grow)
  height            | number              | Fixed height in points (prefer flex_grow)

STYLE PROPS (used in element props):
  Property          | Type                | Values / Notes
  ------------------|---------------------|--------------------------------------------
  background_color  | string              | Hex: "#4285F4", or theme: "ACCENT1"
  border_color      | string              | Hex color string
  color             | string              | Text color, hex string
  font_size         | number              | Points (title: 32-40, body: 16-24)
  font_family       | string              | e.g. "Roboto", "Open Sans", "Montserrat"
  bold              | boolean             | Bold text
  italic            | boolean             | Italic text
  alignment         | string              | "START", "CENTER", "END", "JUSTIFIED"
  content_alignment | string              | "TOP", "MIDDLE", "BOTTOM"

DIMENSIONS:
  All numeric dimensions are in points (1 point = 1/72 inch).
  Default slide size: 720 x 405 points (widescreen 16:9).

WHERE PROPS GO:
  - Slide-level layout: SlideDefinition.layout = {flex_direction, padding, background_color, ...}
  - Element-level: Element.props = {flex_grow, color, font_size, ...}
  - The same layout props work in both places (slides and box elements are both flex containers).
"""

    @mcp.resource("slides://reference/examples")
    def resource_examples() -> str:
        """Gallery of example slide JSON definitions."""
        return """\
EXAMPLE SLIDE GALLERY

1. CENTERED TITLE SLIDE
{"layout": {"flex_direction": "column", "justify_content": "center", "align_items": "center", "padding": 50, "background_color": "#1A1A2E"},
 "children": [
   {"type": "text_box", "text": "Welcome", "props": {"color": "#FFFFFF", "font_size": 44, "bold": true, "alignment": "CENTER"}},
   {"type": "text_box", "text": "A subtitle goes here", "props": {"color": "#AAAACC", "font_size": 22, "alignment": "CENTER", "margin": {"top": 10}}}
 ]}

2. TITLE + BODY SLIDE
{"layout": {"flex_direction": "column", "padding": 40, "background_color": "#FFFFFF"},
 "children": [
   {"type": "text_box", "text": "Key Findings", "props": {"color": "#1A1A2E", "font_size": 32, "bold": true}},
   {"type": "text_box", "text": "Our research shows three important trends:\\n\\n1. First trend with supporting data\\n2. Second trend and its implications\\n3. Third trend and next steps", "props": {"color": "#333333", "font_size": 18, "flex_grow": 1, "margin": {"top": 15}}}
 ]}

3. TWO-COLUMN COMPARISON
{"layout": {"flex_direction": "column", "padding": 40, "background_color": "#FFFFFF"},
 "children": [
   {"type": "text_box", "text": "Before vs After", "props": {"color": "#1A1A2E", "font_size": 32, "bold": true}},
   {"type": "box", "props": {"flex_direction": "row", "gap": 20, "flex_grow": 1, "margin": {"top": 15}},
    "children": [
      {"type": "text_box", "text": "Before:\\n- Manual process\\n- 2 hour turnaround\\n- Error-prone", "props": {"flex_grow": 1, "background_color": "#FFF0F0", "padding": 20, "color": "#333333", "font_size": 16}},
      {"type": "text_box", "text": "After:\\n- Automated pipeline\\n- 5 min turnaround\\n- 99.9% accuracy", "props": {"flex_grow": 1, "background_color": "#F0FFF0", "padding": 20, "color": "#333333", "font_size": 16}}
    ]}
 ]}

4. THREE-COLUMN METRICS
{"layout": {"flex_direction": "column", "padding": 40, "background_color": "#F5F5F5"},
 "children": [
   {"type": "text_box", "text": "Key Metrics", "props": {"color": "#1A1A2E", "font_size": 32, "bold": true, "alignment": "CENTER"}},
   {"type": "box", "props": {"flex_direction": "row", "gap": 15, "flex_grow": 1, "margin": {"top": 20}},
    "children": [
      {"type": "text_box", "text": "Revenue\\n$2.4M\\n+15% YoY", "props": {"flex_grow": 1, "background_color": "#FFFFFF", "padding": 25, "alignment": "CENTER", "font_size": 18, "color": "#333333"}},
      {"type": "text_box", "text": "Users\\n50,000\\n+32% YoY", "props": {"flex_grow": 1, "background_color": "#FFFFFF", "padding": 25, "alignment": "CENTER", "font_size": 18, "color": "#333333"}},
      {"type": "text_box", "text": "NPS\\n72\\n+8 pts", "props": {"flex_grow": 1, "background_color": "#FFFFFF", "padding": 25, "alignment": "CENTER", "font_size": 18, "color": "#333333"}}
    ]}
 ]}

5. IMAGE + TEXT
{"layout": {"flex_direction": "row", "padding": 30, "gap": 30, "background_color": "#FFFFFF"},
 "children": [
   {"type": "image", "image_url": "https://example.com/diagram.png", "props": {"width": 350, "height": 300}},
   {"type": "box", "props": {"flex_direction": "column", "flex_grow": 1, "justify_content": "center"},
    "children": [
      {"type": "text_box", "text": "Architecture Overview", "props": {"color": "#1A1A2E", "font_size": 28, "bold": true}},
      {"type": "text_box", "text": "The system uses a microservices architecture with three main components.", "props": {"color": "#333333", "font_size": 16, "margin": {"top": 15}}}
    ]}
 ]}

6. STYLED BANNER + CONTENT
{"layout": {"flex_direction": "column", "padding": 0, "background_color": "#FFFFFF"},
 "children": [
   {"type": "box", "props": {"background_color": "#4285F4", "padding": 30},
    "children": [
      {"type": "text_box", "text": "Section Title", "props": {"color": "#FFFFFF", "font_size": 36, "bold": true}}
    ]},
   {"type": "box", "props": {"flex_grow": 1, "padding": 30, "flex_direction": "column"},
    "children": [
      {"type": "text_box", "text": "Content below the banner with more detail and explanation.", "props": {"color": "#333333", "font_size": 18}}
    ]}
 ]}
"""

    @mcp.resource("slides://reference/colors")
    def resource_colors() -> str:
        """Color formats, theme colors, and useful hex values."""
        return """\
SLIDES COLOR REFERENCE

COLOR FORMATS:
  Hex strings: "#RRGGBB" e.g. "#4285F4" (Google Blue)
  Theme names: "ACCENT1", "TEXT1", etc. (resolved from presentation theme)

THEME COLOR NAMES:
  ACCENT1, ACCENT2, ACCENT3, ACCENT4, ACCENT5, ACCENT6
  TEXT1, TEXT2
  BACKGROUND1, BACKGROUND2
  HYPERLINK

USEFUL HEX COLORS:
  Dark backgrounds:  #1A1A2E, #16213E, #0F3460, #2C3E50, #1E1E1E
  Light backgrounds: #FFFFFF, #F5F5F5, #F0F4F8, #FAFAFA
  Google colors:     #4285F4 (blue), #EA4335 (red), #FBBC04 (yellow), #34A853 (green)
  Text colors:       #FFFFFF (white), #333333 (dark gray), #666666 (medium gray), #999999 (light gray)
  Accent colors:     #FF6B6B (coral), #4ECDC4 (teal), #45B7D1 (sky blue), #96CEB4 (sage)
  Pastels:           #FFF0F0 (pink tint), #F0FFF0 (green tint), #F0F0FF (blue tint), #FFFFF0 (yellow tint)

WHERE COLORS ARE USED:
  background_color — slide layout or any element (fills the background)
  border_color     — any element (draws a border)
  color            — text_box only (sets text color)
"""

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
