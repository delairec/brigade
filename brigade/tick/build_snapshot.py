from dataclasses import dataclass
from datetime import datetime

from brigade.ledger.format_instant import format_instant

DOCUMENT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class Snapshot:
    now: datetime

    def to_document(self) -> dict:
        return {"schema_version": DOCUMENT_SCHEMA_VERSION, "now": format_instant(self.now)}


def build_snapshot(now: datetime) -> Snapshot:
    return Snapshot(now=now)
