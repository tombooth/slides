from typing import Optional


class Context:
    parents: list["Operation"]

    def __init__(self):
        self.parents = []

    def push(self, operation: "Operation"):
        self.parents.append(operation)

    def find_first[T](self, operation_class: type[T]) -> T:
        for operation in reversed(self.parents):
            if isinstance(operation, operation_class):
                return operation
        raise ValueError(f"No {operation_class.__name__} found in context")


class Operation:
    def __init__(self, **kwargs):
        pass

    def compile(self, context: Optional[Context] = None) -> list[dict]:
        raise NotImplementedError("Please implement compile()")
