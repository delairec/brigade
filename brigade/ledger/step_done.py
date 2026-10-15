from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class StepDone:
    name: ClassVar[str] = "step.done"
    kind: str
    run: str
    step: str

    @classmethod
    def from_document(cls, document: dict) -> "StepDone":
        return cls(kind=document["kind"], run=document["run"], step=document["step"])

    def to_document(self) -> dict:
        return {"kind": self.kind, "run": self.run, "step": self.step}
