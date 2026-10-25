import json
from datetime import datetime

from brigade.inbox.inbox_locations import INBOX_DIRECTORY, LOCK_FILE, SIGNALS_FILE, SIGNALS_SCHEMA_VERSION
from brigade.ledger.format_instant import format_instant
from brigade.system.append_line import append_line
from brigade.system.hold_lock import hold_lock
from brigade.system.paths import Paths


def append_inbox_line(paths: Paths, instant: datetime, fields: dict) -> None:
    line = {"schema_version": SIGNALS_SCHEMA_VERSION, "ts": format_instant(instant), **fields}
    with hold_lock(paths.lock_directory / LOCK_FILE):
        append_line(paths.state_root / INBOX_DIRECTORY / SIGNALS_FILE, json.dumps(line))
