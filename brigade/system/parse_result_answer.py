from dataclasses import dataclass

from brigade.system.reset_hour import ResetHour
from brigade.system.token_usage import TokenUsage

DOCUMENT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ParseResultAnswer:
    outcome: str
    steps: int | None
    usage: TokenUsage | None
    session_id: str | None
    duration_ms: int | None
    cost_usd: float | None
    error_class: str | None
    reset: ResetHour | None
    message: str | None

    @classmethod
    def from_document(cls, document: dict) -> "ParseResultAnswer":
        usage = document["usage"]
        reset = document["reset"]
        return cls(
            outcome=document["outcome"],
            steps=document["steps"],
            usage=None if usage is None else TokenUsage.from_document(usage),
            session_id=document["session_id"],
            duration_ms=document["duration_ms"],
            cost_usd=document["cost_usd"],
            error_class=document["error_class"],
            reset=None if reset is None else ResetHour.from_document(reset),
            message=document["message"],
        )

    def to_document(self) -> dict:
        return {
            "schema_version": DOCUMENT_SCHEMA_VERSION,
            "outcome": self.outcome,
            "steps": self.steps,
            "usage": None if self.usage is None else self.usage.to_document(),
            "session_id": self.session_id,
            "duration_ms": self.duration_ms,
            "cost_usd": self.cost_usd,
            "error_class": self.error_class,
            "reset": None if self.reset is None else self.reset.to_document(),
            "message": self.message,
        }
