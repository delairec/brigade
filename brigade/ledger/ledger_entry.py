from dataclasses import dataclass
from datetime import datetime

from brigade.ledger.declared_events import LedgerEvent


@dataclass(frozen=True)
class LedgerEntry:
    instant: datetime
    event: LedgerEvent
