from datetime import datetime

from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.run_finished import RunFinished
from brigade.tick.decide_resume_at import decide_resume_at

RATE_LIMIT = "rate_limit"


def is_client_on_rate_limit(entries: tuple[LedgerEntry, ...], client: str, now: datetime) -> bool:
    return any(
        isinstance(entry.event, RunFinished)
        and entry.event.error_class == RATE_LIMIT
        and entry.event.client == client
        and decide_resume_at(entry.instant, entry.event.reset) > now
        for entry in entries
    )
