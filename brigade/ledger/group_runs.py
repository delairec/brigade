from collections.abc import Iterable

from brigade.ledger.finished_run import FinishedRun
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.run_finished import RunFinished


def group_runs(entries: Iterable[LedgerEntry]) -> list[FinishedRun]:
    runs: dict[str, FinishedRun] = {}
    for entry in entries:
        if isinstance(entry.event, RunFinished):
            earlier = runs.pop(entry.event.run, None)
            segments = () if earlier is None else earlier.segments
            runs[entry.event.run] = FinishedRun(
                run=entry.event.run, finished_at=entry.instant, segments=(*segments, entry.event)
            )
    return list(runs.values())
