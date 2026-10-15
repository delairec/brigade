import shutil
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from pathlib import Path

from brigade.errors import BrigadeError, CannotWrite
from brigade.ledger.group_runs import group_runs
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.order_done import OrderDone
from brigade.ledger.read_ledger import read_ledger
from brigade.runs.describe_run import describe_run
from brigade.runs.run_locations import (
    REMOVED_RUNS_DIRECTORY,
    RESULT_FILE,
    RUN_RECORD_FILE,
    RUNS_DIRECTORY,
    RUNS_LOCK_FILE,
)
from brigade.system.hold_lock import hold_lock
from brigade.system.paths import Paths

RESUMED_ERROR_CLASS = "rate_limit"
RUNNING = "running"
FINISHED = "finished"
NO_RESUMABLE_RUN_SPARED = frozenset()


@dataclass(frozen=True)
class PruneRequest:
    paths: Paths
    keep: int
    before: date | None = None
    resumable: bool = False
    dry_run: bool = False


@dataclass(frozen=True)
class _SettledRun:
    run: str
    state: str
    settled_at: datetime
    directory: Path


@dataclass(frozen=True)
class PruneOutcome:
    removed: list[dict]
    skipped: list[dict]


@dataclass(frozen=True)
class _ListedRuns:
    newest_first: list[_SettledRun]
    skipped: list[dict]


NO_RUN_LISTED = _ListedRuns(newest_first=[], skipped=[])


def _list_resumable_runs(entries: tuple[LedgerEntry, ...]) -> frozenset[str]:
    finished_runs = group_runs(entries)
    return frozenset(run.run for run in finished_runs if run.last.error_class == RESUMED_ERROR_CLASS)


def _list_done_study_runs(runs_directory: Path, entries: tuple[LedgerEntry, ...]) -> list[_SettledRun]:
    done_entries = {entry.event.run: entry for entry in entries if isinstance(entry.event, OrderDone)}
    return [
        _SettledRun(
            run=directory.name, state=FINISHED, settled_at=done_entries[directory.name].instant, directory=directory
        )
        for directory in sorted(runs_directory.iterdir())
        if directory.name in done_entries
    ]


def _settle(directory: Path, state: str) -> _SettledRun:
    settling_file = directory / (RESULT_FILE if state == FINISHED else RUN_RECORD_FILE)
    settled_at = datetime.fromtimestamp(settling_file.stat().st_mtime, tz=UTC)
    return _SettledRun(run=directory.name, state=state, settled_at=settled_at, directory=directory)


def _list_removable_runs(request: PruneRequest) -> _ListedRuns:
    runs_directory = request.paths.state_root / RUNS_DIRECTORY
    if not runs_directory.is_dir():
        return NO_RUN_LISTED
    entries = read_ledger(request.paths.state_root).entries
    spared = NO_RESUMABLE_RUN_SPARED if request.resumable else _list_resumable_runs(entries)
    states = {}
    skipped = []
    for directory in sorted(runs_directory.iterdir()):
        if not (directory / RUN_RECORD_FILE).is_file() or directory.name in spared:
            continue
        try:
            states[directory] = describe_run(directory)["state"]
        except BrigadeError as error:
            skipped.append({"run": directory.name, "reason": str(error)})
    settled = [_settle(directory, state) for directory, state in states.items() if state != RUNNING]
    settled += _list_done_study_runs(runs_directory, entries)
    newest_first = sorted(settled, key=lambda run: (run.settled_at, run.run), reverse=True)
    return _ListedRuns(newest_first=newest_first, skipped=skipped)


def _select_removed_runs(request: PruneRequest, newest_first: list[_SettledRun]) -> list[_SettledRun]:
    cutoff = None if request.before is None else datetime.combine(request.before, time.min, tzinfo=UTC)
    removed = [
        run
        for rank, run in enumerate(newest_first)
        if rank >= request.keep or (cutoff is not None and run.settled_at < cutoff)
    ]
    return removed[::-1]


def _empty_removed_runs(removed_runs_directory: Path) -> None:
    if not removed_runs_directory.is_dir():
        return
    for entry in removed_runs_directory.iterdir():
        _delete(entry)


def _delete(entry: Path) -> None:
    try:
        if entry.is_dir():
            shutil.rmtree(entry)
        else:
            entry.unlink()
    except OSError as error:
        raise CannotWrite(entry, error) from error


def _remove(run: _SettledRun, removed_runs_directory: Path) -> None:
    try:
        removed_runs_directory.mkdir(parents=True, exist_ok=True)
        removed_directory = run.directory.rename(removed_runs_directory / run.run)
    except OSError as error:
        raise CannotWrite(removed_runs_directory, error) from error
    shutil.rmtree(removed_directory)


def prune_runs(request: PruneRequest) -> PruneOutcome:
    removed_runs_directory = request.paths.state_root / REMOVED_RUNS_DIRECTORY
    with hold_lock(request.paths.lock_directory / RUNS_LOCK_FILE):
        if not request.dry_run:
            _empty_removed_runs(removed_runs_directory)
        listed = _list_removable_runs(request)
        removed = _select_removed_runs(request, listed.newest_first)
        if not request.dry_run:
            for run in removed:
                _remove(run, removed_runs_directory)
    return PruneOutcome(removed=[{"run": run.run, "state": run.state} for run in removed], skipped=listed.skipped)
