import re
from googleapiclient.discovery import build
from google.auth import default
from google.oauth2.credentials import Credentials
from typing import Optional, Union

from .auth.secret import from_secret
from .api_types import Dimension
from .presentation import Presentation

# include DSL functions
from .image import image
from .operation import insert_text
from .page import box
from .shape import text_box


def open(
    url: str, credentials: Optional[Union[Credentials | str]] = None
) -> Presentation:
    """
    Fetches a Google Slides presentation using the API and initializes a Presentation object.
    """
    # Extract the presentation ID from the URL using regex
    match = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
    if not match:
        raise ValueError("Invalid Google Slides URL")
    presentation_id = match.group(1)

    if credentials is None:
        credentials, _ = default(
            scopes=["https://www.googleapis.com/auth/presentations"]
        )
    elif isinstance(credentials, str):
        credentials = from_secret(credentials)

    # Build the Google Slides API service
    service = build("slides", "v1", credentials=credentials)

    # Get the presentation metadata
    presentation = service.presentations().get(presentationId=presentation_id).execute()

    # Extract dimensions
    page_size = presentation["pageSize"]
    width = Dimension(page_size["width"]["magnitude"], page_size["width"]["unit"])
    height = Dimension(page_size["height"]["magnitude"], page_size["height"]["unit"])

    # Initialize and return the Presentation object
    return Presentation(
        id=presentation_id, width=width, height=height, credentials=credentials
    )
