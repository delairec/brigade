from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class BudgetApplied:
    name: ClassVar[str] = "budget.applied"
    role: str
    before: int
    after: int
    segments: int
    restarts: int
    growth: float | None
    restart_tokens: float | None

    @classmethod
    def from_document(cls, document: dict) -> "BudgetApplied":
        return cls(
            role=document["role"],
            before=document["before"],
            after=document["after"],
            segments=document["segments"],
            restarts=document["restarts"],
            growth=document["growth"],
            restart_tokens=document["restart_tokens"],
        )

    def to_document(self) -> dict:
        return {
            "role": self.role,
            "before": self.before,
            "after": self.after,
            "segments": self.segments,
            "restarts": self.restarts,
            "growth": self.growth,
            "restart_tokens": self.restart_tokens,
        }
