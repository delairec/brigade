import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from brigade.errors import BrigadeError, CannotWrite
from brigade.ledger.declared_events import ENVELOPE_KEYS, EVENT_FIELDS, LEDGER_SCHEMA_VERSION
from brigade.ledger.format_instant import format_instant
from brigade.ledger.ledger_locations import LEDGER_DIRECTORY, LOCK_DIRECTORY, LOCK_FILE
from brigade.system.hold_lock import hold_lock

MONTH_FILE_FORMAT = "%Y-%m.jsonl"


class LedgerEventRefused(BrigadeError):
    pass


@dataclass(frozen=True)
class LedgerEvent:
    name: str
    instant: datetime
    fields: dict


def _refuse_malformed(event: LedgerEvent) -> None:
    if event.name not in EVENT_FIELDS:
        raise LedgerEventRefused(f"the event {event.name} is not declared")
    missing = [field for field in EVENT_FIELDS[event.name] if field not in event.fields]
    if missing:
        raise LedgerEventRefused(f"the event {event.name} lacks {', '.join(missing)}")
    envelope_keys = [key for key in ENVELOPE_KEYS if key in event.fields]
    if envelope_keys:
        raise LedgerEventRefused(f"the event {event.name} carries the envelope key {', '.join(envelope_keys)}")
    if event.instant.utcoffset() is None:
        raise LedgerEventRefused(f"the instant of the event {event.name} carries no time zone")


def append_event(state_root: Path, event: LedgerEvent) -> None:
    _refuse_malformed(event)
    instant = event.instant.astimezone(timezone.utc)
    line = json.dumps(
        {"schema_version": LEDGER_SCHEMA_VERSION, "ts": format_instant(instant), "event": event.name, **event.fields}
    )
    ledger_directory = state_root / LEDGER_DIRECTORY
    month_file = ledger_directory / instant.strftime(MONTH_FILE_FORMAT)
    with hold_lock(state_root / LOCK_DIRECTORY / LOCK_FILE):
        try:
            ledger_directory.mkdir(parents=True, exist_ok=True)
            with open(month_file, "a", encoding="utf-8") as ledger_file:
                ledger_file.write(line + "\n")
                ledger_file.flush()
        except OSError as error:
            raise CannotWrite(error.filename or month_file, error) from error
