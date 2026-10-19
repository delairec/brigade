from dataclasses import dataclass
from datetime import datetime

from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.wave_cancelled import WaveCancelled
from brigade.ledger.wave_closed import WaveClosed
from brigade.ledger.wave_paused import WavePaused
from brigade.ledger.wave_reported import WaveReported
from brigade.ledger.wave_resumed import WaveResumed
from brigade.ledger.wave_started import WaveStarted

WAVE_EVENTS = (WaveStarted, WavePaused, WaveResumed, WaveReported, WaveClosed, WaveCancelled)
ENDING_EVENTS = (WaveClosed, WaveCancelled)


@dataclass(frozen=True)
class WaveSummary:
    started: WaveStarted
    started_at: datetime
    last_event: str
    is_open: bool


def _summarize(entries: tuple[LedgerEntry, ...], started: LedgerEntry) -> WaveSummary:
    events = [
        entry.event
        for entry in entries
        if isinstance(entry.event, WAVE_EVENTS) and entry.event.wave == started.event.wave
    ]
    return WaveSummary(
        started=started.event,
        started_at=started.instant,
        last_event=events[-1].name,
        is_open=not any(isinstance(event, ENDING_EVENTS) for event in events),
    )


def summarize_waves(entries: tuple[LedgerEntry, ...]) -> tuple[WaveSummary, ...]:
    return tuple(_summarize(entries, entry) for entry in entries if isinstance(entry.event, WaveStarted))
