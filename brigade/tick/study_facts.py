from dataclasses import dataclass
from datetime import datetime

from brigade.ledger.format_instant import format_instant


@dataclass(frozen=True)
class StudyFacts:
    name: str
    slot: str
    every: str | None
    status: str
    last_started: datetime | None
    parked: bool

    def to_document(self) -> dict:
        return {
            "study": self.name,
            "slot": self.slot,
            "every": self.every,
            "status": self.status,
            "last_started": None if self.last_started is None else format_instant(self.last_started),
            "parked": self.parked,
        }
