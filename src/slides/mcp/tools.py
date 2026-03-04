import re

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from slides.api_types import Dimension
from slides.io.gcs import signed_url_for
from slides.presentation import Presentation

from .models import SlideDefinition
from .translate import build_slide


def _build_slides_service(credentials: Credentials):
    return build("slides", "v1", credentials=credentials)


async def create_presentation(
    title: str,
    credentials: Credentials,
) -> dict:
    service = _build_slides_service(credentials)
    presentation = (
        service.presentations().create(body={"title": title}).execute()
    )

    pres_id = presentation["presentationId"]
    page_size = presentation["pageSize"]

    return {
        "presentation_id": pres_id,
        "url": f"https://docs.google.com/presentation/d/{pres_id}/edit",
        "width": page_size["width"],
        "height": page_size["height"],
    }


async def create_slides(
    presentation_id: str,
    slides: list[SlideDefinition],
    credentials: Credentials,
) -> dict:
    service = _build_slides_service(credentials)

    # Fetch presentation metadata for dimensions
    pres_data = (
        service.presentations().get(presentationId=presentation_id).execute()
    )
    page_size = pres_data["pageSize"]
    width = Dimension(page_size["width"]["magnitude"], page_size["width"]["unit"])
    height = Dimension(page_size["height"]["magnitude"], page_size["height"]["unit"])

    presentation = Presentation(
        id=presentation_id, width=width, height=height, credentials=credentials
    )

    # Build and compile all slides
    slide_objects = [build_slide(presentation, sd) for sd in slides]
    requests = [req for s in slide_objects for req in s.compile()]

    service.presentations().batchUpdate(
        presentationId=presentation_id,
        body={"requests": requests},
    ).execute()

    return {
        "slides_created": len(slides),
        "presentation_id": presentation_id,
        "url": f"https://docs.google.com/presentation/d/{presentation_id}/edit",
    }


async def read_presentation(
    presentation_url: str,
    credentials: Credentials,
) -> dict:
    match = re.search(r"/d/([a-zA-Z0-9-_]+)", presentation_url)
    if not match:
        raise ValueError("Invalid Google Slides URL")
    pres_id = match.group(1)

    service = _build_slides_service(credentials)
    pres_data = (
        service.presentations().get(presentationId=pres_id).execute()
    )

    page_size = pres_data["pageSize"]
    pres_slides = pres_data.get("slides", [])

    return {
        "presentation_id": pres_id,
        "width": page_size["width"],
        "height": page_size["height"],
        "slide_count": len(pres_slides),
        "slide_ids": [s["objectId"] for s in pres_slides],
    }


async def upload_image(
    file_path: str,
    bucket: str,
    credentials: Credentials,
) -> dict:
    url = signed_url_for(
        image=file_path,
        bucket=bucket,
        credentials=credentials,
    )
    return {"signed_url": url}
