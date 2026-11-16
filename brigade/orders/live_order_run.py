from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class LiveOrderRun:
    order: str
    recipe: str
    run: str
    started: datetime
    max_wall: int
