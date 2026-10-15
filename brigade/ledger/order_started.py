from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class OrderStarted:
    name: ClassVar[str] = "order.started"
    project: str | None
    kind: str
    order: str
    run: str

    @classmethod
    def from_document(cls, document: dict) -> "OrderStarted":
        return cls(project=document["project"], kind=document["kind"], order=document["order"], run=document["run"])

    def to_document(self) -> dict:
        return {"project": self.project, "kind": self.kind, "order": self.order, "run": self.run}
