from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class OrderDone:
    name: ClassVar[str] = "order.done"
    project: str
    kind: str

    @classmethod
    def from_document(cls, document: dict) -> "OrderDone":
        return cls(project=document["project"], kind=document["kind"])
