import shutil
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from pathlib import Path

from brigade.ledger.group_runs import group_runs
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


def _list_resumable_runs(state_root: Path) -> frozenset[str]:
    finished_runs = group_runs(read_ledger(state_root).entries)
    return frozenset(run.run for run in finished_runs if run.last.error_class == RESUMED_ERROR_CLASS)


def _settle(directory: Path, state: str) -> _SettledRun:
    settling_file = directory / (RESULT_FILE if state == FINISHED else RUN_RECORD_FILE)
    settled_at = datetime.fromtimestamp(settling_file.stat().st_mtime, tz=UTC)
    return _SettledRun(run=directory.name, state=state, settled_at=settled_at, directory=directory)


def _list_removable_runs(request: PruneRequest) -> list[_SettledRun]:
    runs_directory = request.paths.state_root / RUNS_DIRECTORY
    if not runs_directory.is_dir():
        return []
    spared = NO_RESUMABLE_RUN_SPARED if request.resumable else _list_resumable_runs(request.paths.state_root)
    states = {
        directory: describe_run(directory)["state"]
        for directory in runs_directory.iterdir()
        if (directory / RUN_RECORD_FILE).is_file() and directory.name not in spared
    }
    settled = [_settle(directory, state) for directory, state in states.items() if state != RUNNING]
    return sorted(settled, key=lambda run: (run.settled_at, run.run), reverse=True)


def _select_removed_runs(request: PruneRequest, newest_first: list[_SettledRun]) -> list[_SettledRun]:
    cutoff = None if request.before is None else datetime.combine(request.before, time.min, tzinfo=UTC)
    removed = [
        run
        for rank, run in enumerate(newest_first)
        if rank >= request.keep or (cutoff is not None and run.settled_at < cutoff)
    ]
    return removed[::-1]


def _remove(run: _SettledRun, removed_runs_directory: Path) -> None:
    removed_runs_directory.mkdir(parents=True, exist_ok=True)
    removed_directory = run.directory.rename(removed_runs_directory / run.run)
    shutil.rmtree(removed_directory)


def prune_runs(request: PruneRequest) -> list[dict]:
    with hold_lock(request.paths.lock_directory / RUNS_LOCK_FILE):
        removed = _select_removed_runs(request, _list_removable_runs(request))
        if not request.dry_run:
            for run in removed:
                _remove(run, request.paths.state_root / REMOVED_RUNS_DIRECTORY)
    return [{"run": run.run, "state": run.state} for run in removed]
