from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.wave_started import WaveStarted
from brigade.waves.summarize_waves import summarize_waves


def list_open_waves(entries: tuple[LedgerEntry, ...], project: str) -> tuple[WaveStarted, ...]:
    return tuple(
        summary.started
        for summary in summarize_waves(entries)
        if summary.is_open and summary.started.project == project
    )
