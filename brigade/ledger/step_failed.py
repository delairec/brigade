from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class StepFailed:
    name: ClassVar[str] = "step.failed"
    kind: str
    run: str
    step: str
    reason: str

    @classmethod
    def from_document(cls, document: dict) -> "StepFailed":
        return cls(kind=document["kind"], run=document["run"], step=document["step"], reason=document["reason"])

    def to_document(self) -> dict:
        return {"kind": self.kind, "run": self.run, "step": self.step, "reason": self.reason}
