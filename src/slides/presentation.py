import json

from googleapiclient.discovery import build
from google.auth import default
from google.oauth2.credentials import Credentials
from typing import Optional

from .api_types import Dimension
from .object import Object
from .page import Slide


class Presentation:

    def __init__(self, id: str, width: Dimension, height: Dimension):
        self.id = id
        self.width = width
        self.height = height

    def begin(self) -> "Transaction":
        return Transaction(self)


class Transaction:
    def __init__(self, presentation: Presentation):
        self.presentation = presentation
        self._to_compile = []

    def slide(self, **kwargs) -> Slide:
        """
        Creates or updates a slide.

        If you want to update, pass in an object_id
        """

        default_kwargs = {
            "width": self.presentation.width,
            "height": self.presentation.height,
        }
        merged_kwargs = {**default_kwargs, **kwargs}
        slide = Slide(**merged_kwargs)

        self._to_compile.append(slide)

        return slide

    def compile(self) -> list[dict]:
        """
        Compiles changes into a batch update set of operations
        """

        updates = []

        for object in self._to_compile:
            updates += object.compile()

        return updates

    def commit(self, credentials: Optional[Credentials] = None):
        """
        Commits the changes to the presentation
        """

        updates = self.compile()

        print(json.dumps(updates))

        if credentials is None:
            credentials, _ = default(
                scopes=["https://www.googleapis.com/auth/presentations"]
            )

        # Build the Google Slides API service
        service = build("slides", "v1", credentials=credentials)
        print(
            service.presentations()
            .batchUpdate(
                presentationId=self.presentation.id,
                body={"requests": updates},
            )
            .execute()
        )
