import re

from brigade.errors import BrigadeError
from brigade.ledger.format_instant import format_instant
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.wave_started import WaveStarted

WAVE_NUMBER_MARK = "_w"


def _read_wave_number(entry: LedgerEntry, prefix: str) -> int:
    number = re.fullmatch(rf"{re.escape(prefix)}(\d+)", entry.event.wave)
    if number is None:
        raise BrigadeError(
            f"the wave.started of {format_instant(entry.instant)} names the wave {entry.event.wave}, not {prefix}<n>"
        )
    return int(number.group(1))


def name_next_wave(project: str, entries: tuple) -> str:
    prefix = f"{project}{WAVE_NUMBER_MARK}"
    numbers = [
        _read_wave_number(entry, prefix)
        for entry in entries
        if isinstance(entry.event, WaveStarted) and entry.event.project == project
    ]
    return f"{prefix}{max(numbers, default=0) + 1}"
