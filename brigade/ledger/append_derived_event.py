from collections.abc import Callable
from datetime import datetime

from brigade.ledger.ledger_locations import LOCK_FILE
from brigade.ledger.read_ledger import LedgerReading, read_ledger
from brigade.ledger.wave_started import WaveStarted
from brigade.ledger.write_event_line import write_event_line
from brigade.system.hold_lock import hold_lock
from brigade.system.paths import Paths


def append_derived_event(paths: Paths, instant: datetime, derive: Callable[[LedgerReading], WaveStarted]) -> dict:
    with hold_lock(paths.lock_directory / LOCK_FILE):
        return write_event_line(paths, instant, derive(read_ledger(paths.state_root)))
