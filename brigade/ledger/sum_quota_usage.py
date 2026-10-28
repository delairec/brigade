from datetime import datetime, timedelta

from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.run_finished import RunFinished

USAGE_MEASURES = ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")


def sum_quota_usage(entries: tuple[LedgerEntry, ...], now: datetime, window_hours: int) -> dict:
    window_start = now - timedelta(hours=window_hours)
    finished = [
        entry.event for entry in entries if isinstance(entry.event, RunFinished) and entry.instant >= window_start
    ]
    reported = [run.usage for run in finished if run.usage is not None]
    return {
        "window_hours": window_hours,
        "usage": {measure: sum(getattr(usage, measure) for usage in reported) for measure in USAGE_MEASURES},
        "runs_without_usage": len(finished) - len(reported),
    }
