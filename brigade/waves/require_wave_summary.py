from brigade.errors import BrigadeError
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.waves.summarize_waves import WaveSummary, summarize_waves


def require_wave_summary(entries: tuple[LedgerEntry, ...], wave: str) -> WaveSummary:
    for summary in summarize_waves(entries):
        if summary.started.wave == wave:
            return summary
    raise BrigadeError(f"no wave.started names the wave {wave}")
