from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class LedgerEntry:
    instant: datetime
    event: object
