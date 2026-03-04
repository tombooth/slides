# MCP Server for Google Slides Generation

## Context

The `slides` library provides a Python API using Yoga flexbox to lay out Google Slides. We want Claude Code to generate slides autonomously via an MCP server over HTTPS (streamable-http transport).

**Auth model (two separate concerns):**
- **User's Google OAuth** — for all Slides API operations (create/read/write presentations). The user authenticates via browser-based Google OAuth, and the MCP server acts as an OAuth relay. Each user's presentations stay under their own Google account.
- **Server's service account** — for GCS bucket writes (image uploads). Configured at deployment time. Users don't need GCS permissions.

**Dependencies managed with `uv`.** Implementation via **red/green TDD**.

## Package Structure

```
src/slides/mcp/
    __init__.py          # Package marker
    __main__.py          # Entry point: python -m slides.mcp
    server.py            # FastMCP server setup
    auth_provider.py     # OAuthAuthorizationServerProvider (Google OAuth relay)
    tools.py             # Tool definitions
    models.py            # Pydantic models for tool input schemas
    translate.py         # JSON → slides DSL translation
tests/
    test_mcp_models.py       # Model validation tests
    test_mcp_translate.py    # JSON → DSL → API requests tests
    test_mcp_auth_provider.py # OAuth provider tests (mocked Google)
    test_mcp_tools.py        # Tool function tests (mocked APIs)
Dockerfile
```

The MCP server lives inside the `slides` package as `slides.mcp` subpackage. Run with `python -m slides.mcp`.

## Auth Design: MCP OAuth → Google OAuth Relay

The MCP SDK's `OAuthAuthorizationServerProvider` protocol supports exactly this pattern (from the SDK docstring):

```
+--------+     +------------+     +-------------------+
| Claude | --> | MCP Server | --> | Google OAuth       |
| Code   |     |            |     | (accounts.google)  |
+--------+     +------------+     +-------------------+
                    |   ^                  |
+------------+      |   |    Redirect      |
|redirect_uri|<-----+   +------------------+
+------------+
```

**Flow:**
1. Claude Code connects to MCP server over HTTPS
2. MCP server requires auth → Claude Code discovers OAuth endpoints
3. Claude Code opens browser to MCP server's `/authorize`
4. MCP server's `authorize()` builds Google OAuth URL and redirects browser there
5. User consents on Google → Google redirects to MCP server's callback (e.g. `/google/callback`)
6. MCP server exchanges Google auth code for Google tokens, stores them, generates its own auth code
7. MCP server redirects to Claude Code's `redirect_uri` with its auth code
8. Claude Code calls MCP server's `/token` to exchange auth code for MCP access token
9. Tool calls include MCP access token → server maps it to stored Google tokens → uses them for Slides API

**Implementation (`auth_provider.py`):**
- Implement `OAuthAuthorizationServerProvider` protocol
- In-memory stores for: clients, auth codes → Google tokens, access tokens → Google tokens
- Additional Starlette route for `/google/callback` to complete the Google OAuth leg
- Google OAuth scopes: `presentations` (read/write slides)
- Pass to `FastMCP(auth_server_provider=provider)`

**Service account (for GCS):**
- Loaded from `GOOGLE_APPLICATION_CREDENTIALS` env var or mounted key file
- Used only by `upload_image` tool, independent of user OAuth

**Env vars:**

| Var | Purpose |
|-----|---------|
| `GOOGLE_CLIENT_ID` | OAuth client ID (from Google Cloud Console) |
| `GOOGLE_CLIENT_SECRET` | OAuth client secret |
| `SLIDES_GCS_BUCKET` | GCS bucket for image uploads (optional) |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account key for GCS (optional, only if bucket set) |

## Tools

### Tool 1: `create_presentation`

Creates a new blank Google Slides presentation under the user's account.

**Input:** `title: str`
**Output:** JSON with presentation ID, URL, and dimensions.
**Implementation:** Calls `service.presentations().create(body={"title": title})` using the user's Google credentials from auth context.

### Tool 2: `create_slides`

Creates one or more slides in an existing presentation using flexbox layout.

**Input (`models.py`):**
```python
class Element(BaseModel):
    type: Literal["box", "text_box", "image"]
    props: dict = {}          # Yoga layout + style props
    text: str | None = None   # For text_box elements
    image_url: str | None = None  # For image elements
    children: list["Element"] = []

class SlideDefinition(BaseModel):
    layout: dict = {}         # Flexbox props for the slide root
    object_id: str | None = None  # If set, replaces existing slide
    children: list[Element] = []
```

**Props reference (for tool description):**
- Layout: `flex_direction` (column/row), `justify_content`, `align_content`, `flex_grow`, `gap`, `padding`, `margin`, `width`, `height`, `border`
- Style: `background_color` (#hex), `border_color` (#hex), `color` (#hex text color), `alignment` (START/CENTER/END/JUSTIFIED), `content_alignment` (TOP/MIDDLE/BOTTOM)

### Tool 3: `read_presentation`

Reads structure of an existing presentation.

**Input:** `presentation_url: str`
**Output:** JSON with ID, dimensions, slide count, slide object IDs.

### Tool 4: `upload_image`

Uploads a local file or URL to GCS, returns signed URL for use in `create_slides`.

**Input:** `file_path: str`
**Output:** Signed URL (15-min expiry).
**Auth:** Uses server's service account, not user credentials.
**Only registered** if `SLIDES_GCS_BUCKET` env var is set.

## JSON → DSL Translation (`translate.py`)

Recursive function `build_element(el: Element)` that maps JSON to library calls:

```
Element(type="text_box", props={...}, text="Hi") → text_box(**props)(insert_text("Hi"))
Element(type="box", props={...}, children=[...])  → box(**props)(*[build_element(c) for c in children])
Element(type="image", image_url="...", props={...}) → image(image_url, **props)
```

Slide-level: `build_slide(presentation, slide_def)`:
```
SlideDefinition(layout={...}, children=[...])
  → presentation.slide(**layout)(*[build_element(c) for c in children])
```

**This is the core testable unit.** We can call `build_element()` → `.compile()` and assert on the generated Google Slides API requests without hitting any real API.

## Server Wiring (`server.py`)

```python
from mcp.server.fastmcp import FastMCP
from .auth_provider import GoogleOAuthProvider

provider = GoogleOAuthProvider(
    client_id=os.environ["GOOGLE_CLIENT_ID"],
    client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
)

mcp = FastMCP(
    "google-slides",
    auth_server_provider=provider,
    instructions="Create and edit Google Slides presentations using flexbox layout.",
)

# Import and register tools from tools.py
# Add Google callback route to the underlying Starlette app
```

## `__main__.py`

```python
from .server import mcp

mcp.run(transport="streamable-http")
```

Run with: `python -m slides.mcp`

## pyproject.toml Changes

```toml
# Add to dependencies:
# mcp>=1.26.0
# (rest already present via slides package)
```

## Dockerfile

```dockerfile
FROM python:3.11-slim
COPY . /app
WORKDIR /app
RUN pip install uv && uv sync
EXPOSE 8000
CMD ["uv", "run", "python", "-m", "slides.mcp"]
```

## TDD Implementation Order

Each step: write failing test → implement → test passes.

### Step 1: Models (`tests/test_mcp_models.py` → `src/slides/mcp/models.py`) ✅ DONE
- Test Element validates type field (literal constraint)
- Test Element recursive children
- Test SlideDefinition with layout props
- Test SlideDefinition with optional object_id

### Step 2: Translation (`tests/test_mcp_translate.py` → `src/slides/mcp/translate.py`)
- Test `build_element` with a text_box → compile → assert `createShape` + `insertText` requests
- Test `build_element` with a box containing children → compile → assert nested requests
- Test `build_element` with an image → compile → assert `createImage` request
- Test `build_slide` with layout props → compile → assert slide-level layout
- Test `build_slide` with object_id → compile → assert `deleteObject` + `createSlide` (update flow)
- Test full slide with nested elements (title + two-column body)

### Step 3: Auth Provider (`tests/test_mcp_auth_provider.py` → `src/slides/mcp/auth_provider.py`)
- Test `authorize()` returns Google OAuth URL with correct params
- Test `exchange_authorization_code()` returns valid token when code maps to stored Google creds
- Test `load_access_token()` retrieves stored token
- Test `revoke_token()` removes stored token
- Mock Google's token endpoint for code exchange

### Step 4: Tools (`tests/test_mcp_tools.py` → `src/slides/mcp/tools.py`)
- Test `create_presentation` with mocked Google API → assert `presentations().create()` called with title
- Test `create_slides` with mocked `slides.open()` and `presentation.batch()` → assert correct DSL objects built
- Test `read_presentation` with mocked Google API → assert correct structure returned
- Test `upload_image` with mocked GCS client → assert file uploaded and signed URL returned

### Step 5: Server integration (`src/slides/mcp/server.py` + `src/slides/mcp/__main__.py`)
- Wire FastMCP with auth provider and tools
- Verify server starts and tools are listed

## Files to Create

| File | Purpose |
|------|---------|
| `src/slides/mcp/__init__.py` | Package marker ✅ |
| `src/slides/mcp/__main__.py` | Entry point: `python -m slides.mcp` |
| `src/slides/mcp/models.py` | Pydantic models (Element, SlideDefinition) ✅ |
| `src/slides/mcp/translate.py` | JSON → slides DSL translation |
| `src/slides/mcp/auth_provider.py` | Google OAuth relay implementing MCP OAuth provider |
| `src/slides/mcp/tools.py` | Tool function implementations |
| `src/slides/mcp/server.py` | FastMCP server setup |
| `tests/test_mcp_models.py` | Model tests ✅ |
| `tests/test_mcp_translate.py` | Translation tests |
| `tests/test_mcp_auth_provider.py` | Auth provider tests |
| `tests/test_mcp_tools.py` | Tool tests |
| `Dockerfile` | Container build |

## Files to Modify

| File | Change |
|------|--------|
| `pyproject.toml` | Add `mcp` dependency ✅ |

## Current Progress

- **Step 1 (Models):** ✅ Complete — 12 tests passing
- **Step 2 (Translation):** ✅ Complete — 7 tests passing
- **Step 3 (Auth Provider):** ✅ Complete — 8 tests passing
- **Step 4 (Tools):** ✅ Complete — 5 tests passing
- **Step 5 (Server Wiring):** ✅ Complete — server.py, __main__.py, Dockerfile, pyproject.toml

## Environment Notes

- `pyyoga` (compiled C++ yoga binding) cannot be pip-installed in this environment; a mock module is installed at `/home/claude/.local/lib/python3.11/site-packages/pyyoga.py` for testing
- Tests run with: `export PATH="$HOME/.local/bin:$PATH" && PYTHONPATH=src pytest tests/test_mcp_*.py -v`
