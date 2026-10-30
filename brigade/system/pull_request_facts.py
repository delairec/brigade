from dataclasses import dataclass
from datetime import datetime

from brigade.ledger.format_instant import format_instant


@dataclass(frozen=True)
class CheckVerdict:
    name: str
    verdict: str


@dataclass(frozen=True)
class PullRequestFacts:
    number: int
    state: str
    checks: tuple[CheckVerdict, ...]
    review: str | None
    behind: bool
    head: str
    base: str
    updated_at: datetime

    @classmethod
    def from_document(cls, document: dict) -> "PullRequestFacts":
        return cls(
            number=document["number"],
            state=document["state"],
            checks=tuple(CheckVerdict(name=check["name"], verdict=check["verdict"]) for check in document["checks"]),
            review=document["review"],
            behind=document["behind"],
            head=document["head"],
            base=document["base"],
            updated_at=datetime.fromisoformat(document["updated_at"]),
        )

    def to_document(self) -> dict:
        return {
            "number": self.number,
            "state": self.state,
            "checks": [{"name": check.name, "verdict": check.verdict} for check in self.checks],
            "review": self.review,
            "behind": self.behind,
            "head": self.head,
            "base": self.base,
            "updated_at": format_instant(self.updated_at),
        }
