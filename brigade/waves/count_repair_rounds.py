from datetime import UTC

from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.run_finished import RunFinished
from brigade.ledger.task_state import TaskState
from brigade.ledger.task_verdict import TaskVerdict
from brigade.system.instant_formats import COMPACT_INSTANT_FORMAT
from brigade.waves.is_requeue import is_requeue

REBASE_SLOT = "rebase"
FIXING_STATE = "fixing"
PAUSED_ON_QUOTA_STATE = "paused:quota"
RATE_LIMIT = "rate_limit"


def _is_launched_by(entry: LedgerEntry, run: str) -> bool:
    return run.startswith(f"{entry.instant.astimezone(UTC).strftime(COMPACT_INSTANT_FORMAT)}-")


def _is_rebase_launch(entry: LedgerEntry, runs: tuple[dict, ...]) -> bool:
    return any(
        run["slot"] == REBASE_SLOT
        and run["wave"] == entry.event.wave
        and run["task"] == entry.event.task
        and _is_launched_by(entry, run["run"])
        for run in runs
    )


def _is_rate_limited_launch(entry: LedgerEntry, entries: tuple[LedgerEntry, ...]) -> bool:
    return any(
        isinstance(finished.event, RunFinished)
        and finished.event.error_class == RATE_LIMIT
        and finished.event.wave == entry.event.wave
        and finished.event.task == entry.event.task
        and _is_launched_by(entry, finished.event.run)
        for finished in entries
    )


def _is_spending_round(
    entry: LedgerEntry, entries: tuple[LedgerEntry, ...], runs: tuple[dict, ...], previous_state: str | None
) -> bool:
    return (
        previous_state != PAUSED_ON_QUOTA_STATE
        and not _is_rebase_launch(entry, runs)
        and not _is_rate_limited_launch(entry, entries)
    )


def _restarts_the_rounds(event, wave: str) -> bool:
    return is_requeue(event, wave) or (isinstance(event, TaskVerdict) and event.wave == wave)


def count_repair_rounds(entries: tuple[LedgerEntry, ...], runs: tuple[dict, ...], wave: str) -> dict:
    rounds = {}
    states = {}
    for entry in entries:
        event = entry.event
        if _restarts_the_rounds(event, wave):
            rounds[event.task] = 0
        elif (
            isinstance(event, TaskState)
            and event.wave == wave
            and event.state == FIXING_STATE
            and _is_spending_round(entry, entries, runs, states.get(event.task))
        ):
            rounds[event.task] = rounds.get(event.task, 0) + 1
        if isinstance(event, TaskState) and event.wave == wave:
            states[event.task] = event.state
    return rounds
