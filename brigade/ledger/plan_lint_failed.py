from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class PlanLintFailed:
    name: ClassVar[str] = "plan.lint_failed"
    request: str
    run: str | None

    @classmethod
    def from_document(cls, document: dict) -> "PlanLintFailed":
        return cls(request=document["request"], run=document["run"])

    def to_document(self) -> dict:
        return {"request": self.request, "run": self.run}
