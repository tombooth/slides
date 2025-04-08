import json

from googleapiclient.discovery import build
from google.auth import default
from google.oauth2.credentials import Credentials
from typing import Optional

from .api_types import Dimension
from .page import Slide


class Presentation:

    def __init__(
        self,
        id: str,
        width: Dimension,
        height: Dimension,
        credentials: Optional[Credentials] = None,
    ):
        self.id = id
        self.width = width
        self.height = height
        self._credentials = credentials

    def slide(self, **kwargs) -> Slide:
        """
        Creates or updates a slide.

        If you want to update, pass in an object_id
        """

        default_kwargs = {
            "width": self.width,
            "height": self.height,
        }
        merged_kwargs = {**default_kwargs, **kwargs}
        slide = Slide(**merged_kwargs)

        return slide

    def batch(self, *slides: list[Slide], credentials: Optional[Credentials] = None):
        """
        Batches the changes to the presentation
        """

        requests = [request for slide in slides for request in slide.compile()]

        print(json.dumps(requests))

        if credentials is None:
            if self._credentials is not None:
                credentials = self._credentials
            else:
                credentials, _ = default(
                    scopes=["https://www.googleapis.com/auth/presentations"]
                )

        # Build the Google Slides API service
        service = build("slides", "v1", credentials=credentials)
        print(
            service.presentations()
            .batchUpdate(
                presentationId=self.id,
                body={"requests": requests},
            )
            .execute()
        )
