from .object import Object


class Page(Object):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class Slide(Page):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def compile(self) -> list[dict]:
        if self._new:
            return [{"createSlide": {"objectId": self.object_id}}]
        else:
            return [
                {
                    "deleteObject": {
                        "objectId": self.object_id,
                    }
                },
                {"createSlide": {"objectId": self.object_id}},
            ]
