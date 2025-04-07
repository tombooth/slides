from pyyoga import YogaNode
from typing import Optional


class Layout:
    parents: list["Operation"]

    def __init__(self, *parents: list["Operation"]):
        self.parents = parents

    def calculate(self) -> "Layout":
        self.parents[-1].node().calculate_layout()
        return self

    def push(self, operation: "Operation"):
        return Layout(operation, *self.parents)

    # def first_parent[T](self, operation_class: type[T]) -> T:
    def first_parent(self, operation_class: type) -> any:
        for operation in self.parents:
            if isinstance(operation, operation_class):
                return operation
        raise ValueError(f"No {operation_class.__name__} found in layout")

    def get(self) -> tuple[float, float, float, float]:
        (current_x, current_y, w, h) = self.parents[0].node().get_layout()

        parents = [parent.node().get_layout() for parent in self.parents[1:]]
        parent_x = sum(x for x, _, _, _ in parents)
        parent_y = sum(y for _, y, _, _ in parents)

        return (
            current_x + parent_x,
            current_y + parent_y,
            w,
            h,
        )


class Operation:
    def __init__(self, **kwargs):
        pass

    def compile(self, layout: Optional[Layout] = None) -> list[dict]:
        raise NotImplementedError("Please implement compile()")

    def node(self) -> Optional[YogaNode]:
        return None
