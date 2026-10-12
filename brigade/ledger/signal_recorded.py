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
    wall_limit_s: float | None = None
    steps: int | None = None

    @classmethod
    def from_document(cls, document: dict) -> "SignalRecorded":
        return cls(
            signal=document["signal"],
            project=document["project"],
            procedure=document["procedure"],
            run=document["run"],
            segment=document["segment"],
            budget=document["budget"],
            wall_limit_s=document.get("wall_limit_s"),
            steps=document.get("steps"),
        )

    def to_document(self) -> dict:
        limit = {} if self.wall_limit_s is None else {"wall_limit_s": self.wall_limit_s}
        steps = {} if self.steps is None else {"steps": self.steps}
        return {
            "signal": self.signal,
            "project": self.project,
            "procedure": self.procedure,
            "run": self.run,
            "segment": self.segment,
            "budget": self.budget,
            **limit,
            **steps,
        }
