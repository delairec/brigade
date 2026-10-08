from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class RunFinished:
    name: ClassVar[str] = "run.finished"
    run: str
    segment: int
    procedure: str
    slot: str
    role: str
    client: str
    project: str | None
    session: str | None
    steps: int | None
    duration_ms: int
    usage: dict | None
    outcome: str
    error_class: str | None
    exit: int | None
    wave: str | None
    task: str | None
    nulls: dict
    steps_to_first_edit: int | None = None
    oversized_output_steps: int | None = None

    @classmethod
    def from_document(cls, document: dict) -> "RunFinished":
        return cls(
            run=document["run"],
            segment=document["segment"],
            procedure=document["procedure"],
            slot=document["slot"],
            role=document["role"],
            client=document["client"],
            project=document["project"],
            session=document["session"],
            steps=document["steps"],
            duration_ms=document["duration_ms"],
            usage=document["usage"],
            outcome=document["outcome"],
            error_class=document["error_class"],
            exit=document["exit"],
            wave=document["wave"],
            task=document["task"],
            nulls=document["nulls"],
            steps_to_first_edit=document.get("steps_to_first_edit"),
            oversized_output_steps=document.get("oversized_output_steps"),
        )

    def to_document(self) -> dict:
        reported_measures = {
            "steps_to_first_edit": self.steps_to_first_edit,
            "oversized_output_steps": self.oversized_output_steps,
        }
        return {
            "run": self.run,
            "segment": self.segment,
            "procedure": self.procedure,
            "slot": self.slot,
            "role": self.role,
            "client": self.client,
            "project": self.project,
            "session": self.session,
            "steps": self.steps,
            "duration_ms": self.duration_ms,
            "usage": self.usage,
            "outcome": self.outcome,
            "error_class": self.error_class,
            "exit": self.exit,
            "wave": self.wave,
            "task": self.task,
            "nulls": self.nulls,
            **{measure: value for measure, value in reported_measures.items() if value is not None},
        }
