from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class SignalRecorded:
    name: ClassVar[str] = "signal.recorded"
    signal: str
    project: str | None
    procedure: str
    run: str
    segment: int
    budget: int

    @classmethod
    def from_document(cls, document: dict) -> "SignalRecorded":
        return cls(
            signal=document["signal"],
            project=document["project"],
            procedure=document["procedure"],
            run=document["run"],
            segment=document["segment"],
            budget=document["budget"],
        )

    def to_document(self) -> dict:
        return {
            "signal": self.signal,
            "project": self.project,
            "procedure": self.procedure,
            "run": self.run,
            "segment": self.segment,
            "budget": self.budget,
        }
