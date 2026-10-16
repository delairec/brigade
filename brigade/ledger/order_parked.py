from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class OrderParked:
    name: ClassVar[str] = "order.parked"
    project: str | None
    kind: str
    order: str
    run: str
    step: str
    reason: str

    @classmethod
    def from_document(cls, document: dict) -> "OrderParked":
        return cls(
            project=document["project"],
            kind=document["kind"],
            order=document["order"],
            run=document["run"],
            step=document["step"],
            reason=document["reason"],
        )

    def to_document(self) -> dict:
        return {
            "project": self.project,
            "kind": self.kind,
            "order": self.order,
            "run": self.run,
            "step": self.step,
            "reason": self.reason,
        }
