import json
from datetime import UTC, datetime

from brigade.errors import BrigadeError, CannotWrite
from brigade.ledger.declared_events import LEDGER_SCHEMA_VERSION
from brigade.ledger.forge_account_unavailable import ForgeAccountUnavailable
from brigade.ledger.format_instant import format_instant
from brigade.ledger.ledger_locations import LEDGER_DIRECTORY, LOCK_FILE
from brigade.ledger.run_finished import RunFinished
from brigade.ledger.signal_recorded import SignalRecorded
from brigade.system.hold_lock import hold_lock
from brigade.system.paths import Paths

MONTH_FILE_FORMAT = "%Y-%m.jsonl"


class LedgerEventRefused(BrigadeError):
    pass


def append_event(
    paths: Paths, instant: datetime, event: RunFinished | SignalRecorded | ForgeAccountUnavailable
) -> None:
    if instant.utcoffset() is None:
        raise LedgerEventRefused(f"the instant of the event {event.name} carries no time zone")
    utc_instant = instant.astimezone(UTC)
    line = json.dumps(
        {
            "schema_version": LEDGER_SCHEMA_VERSION,
            "ts": format_instant(utc_instant),
            "event": event.name,
            **event.to_document(),
        }
    )
    ledger_directory = paths.state_root / LEDGER_DIRECTORY
    month_file = ledger_directory / utc_instant.strftime(MONTH_FILE_FORMAT)
    with hold_lock(paths.lock_directory / LOCK_FILE):
        try:
            ledger_directory.mkdir(parents=True, exist_ok=True)
            with open(month_file, "a", encoding="utf-8") as ledger_file:
                ledger_file.write(line + "\n")
                ledger_file.flush()
        except OSError as error:
            raise CannotWrite(error.filename or month_file, error) from error
