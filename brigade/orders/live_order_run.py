from dataclasses import dataclass
from datetime import datetime

from brigade.ledger.format_instant import format_instant


@dataclass(frozen=True)
class LiveOrderRun:
    order: str
    recipe: str
    run: str
    started: datetime
    max_wall: int

    def to_document(self) -> dict:
        return {
            "order": self.order,
            "recipe": self.recipe,
            "run": self.run,
            "started": format_instant(self.started),
            "max_wall": self.max_wall,
        }
