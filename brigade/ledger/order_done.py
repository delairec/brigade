from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class OrderDone:
    name: ClassVar[str] = "order.done"
    project: str | None
    kind: str
    order: str | None = None
    run: str | None = None

    @classmethod
    def from_document(cls, document: dict) -> "OrderDone":
        return cls(
            project=document["project"], kind=document["kind"], order=document.get("order"), run=document.get("run")
        )

    def to_document(self) -> dict:
        return {"project": self.project, "kind": self.kind, "order": self.order, "run": self.run}
