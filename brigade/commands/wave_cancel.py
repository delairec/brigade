import functools
from pathlib import Path

from brigade.command import Argument, Command
from brigade.errors import BrigadeError
from brigade.ledger.append_derived_event import append_derived_event
from brigade.ledger.read_ledger import LedgerReading, read_ledger
from brigade.ledger.task_pr_opened import TaskPrOpened
from brigade.ledger.wave_cancelled import WaveCancelled
from brigade.runs.list_runs import list_runs
from brigade.runs.stop_run import stop_run
from brigade.runtime import Runtime
from brigade.system.render_table import render_table
from brigade.waves.find_last_task_event import find_last_task_event
from brigade.waves.require_wave_summary import require_wave_summary

DOCUMENT_SCHEMA_VERSION = 1
USER_REASON = "user"
LIVE_STATE = "running"
ABSENT = "-"
TASK_HEADER = ("task", "stopped run", "worktree", "branch", "pull request")
TASK_COLUMNS = ("task", "stopped_run", "worktree", "branch", "pull_request")


def _show(value) -> str:
    return ABSENT if value is None else str(value)


def _render_text(document: dict) -> str:
    rows = [tuple(_show(task[column]) for column in TASK_COLUMNS) for task in document["tasks"]]
    return "\n".join([f"wave {document['wave']} cancelled", render_table(TASK_HEADER, rows)])


def _read_request(options):
    return options


def _decide_exit_code(document: dict) -> int:
    return 0


def _derive_cancellation(wave: str, reading: LedgerReading) -> WaveCancelled:
    summary = require_wave_summary(reading.entries, wave)
    if not summary.is_open:
        raise BrigadeError(f"the wave {wave} ended on {summary.last_event}")
    return WaveCancelled(wave=wave, reason=USER_REASON)


def _stop_live_run(state_root: Path, task_runs: list[dict]) -> dict | None:
    live = next((run for run in task_runs if run["state"] == LIVE_STATE), None)
    return None if live is None else stop_run(state_root, live["run"])


def _cancel_task(state_root: Path, runs: list[dict], events: tuple, wave: str, task: str) -> dict:
    task_runs = [run for run in runs if run["wave"] == wave and run["task"] == task]
    stopped = _stop_live_run(state_root, task_runs)
    opened = find_last_task_event(events, TaskPrOpened, wave, task)
    return {
        "task": task,
        "stopped_run": None if stopped is None else stopped["run"],
        "worktree": task_runs[-1]["worktree"] if task_runs else None,
        "branch": None if opened is None else opened.branch,
        "pull_request": None if opened is None else opened.pr,
    }


def wave_cancel(request, runtime: Runtime) -> dict:
    state_root = runtime.paths.state_root
    append_derived_event(runtime.paths, runtime.now, functools.partial(_derive_cancellation, request.wave))
    entries = read_ledger(state_root).entries
    started = require_wave_summary(entries, request.wave).started
    events = tuple(entry.event for entry in entries)
    runs = list_runs(state_root)["runs"]
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "wave": started.wave,
        "tasks": [_cancel_task(state_root, runs, events, started.wave, task) for task in started.tasks],
    }


COMMAND = Command(
    path=("wave", "cancel"),
    help="cancel an open wave: stop the live runs of its tasks and list what stays in place",
    arguments=(Argument(("wave",), {"help": "the name of an open wave of the ledger"}),),
    run=wave_cancel,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
