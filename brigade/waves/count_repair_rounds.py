from datetime import UTC

from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.task_state import TaskState
from brigade.system.instant_formats import COMPACT_INSTANT_FORMAT

REBASE_SLOT = "rebase"
FIXING_STATE = "fixing"


def _is_rebase_launch(entry: LedgerEntry, runs: tuple[dict, ...]) -> bool:
    launched = f"{entry.instant.astimezone(UTC).strftime(COMPACT_INSTANT_FORMAT)}-"
    return any(
        run["slot"] == REBASE_SLOT
        and run["wave"] == entry.event.wave
        and run["task"] == entry.event.task
        and run["run"].startswith(launched)
        for run in runs
    )


def count_repair_rounds(entries: tuple[LedgerEntry, ...], runs: tuple[dict, ...], wave: str) -> dict:
    rounds = {}
    for entry in entries:
        event = entry.event
        if (
            isinstance(event, TaskState)
            and event.wave == wave
            and event.state == FIXING_STATE
            and not _is_rebase_launch(entry, runs)
        ):
            rounds[event.task] = rounds.get(event.task, 0) + 1
    return rounds
