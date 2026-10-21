from brigade.command import Argument, Command
from brigade.ledger.format_instant import format_instant
from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.run_finished import RunFinished
from brigade.ledger.task_pr_opened import TaskPrOpened
from brigade.runtime import Runtime
from brigade.system.render_table import render_table
from brigade.waves.find_last_task_event import find_last_task_event
from brigade.waves.read_task_states import read_task_states
from brigade.waves.require_wave_summary import require_wave_summary

DOCUMENT_SCHEMA_VERSION = 1
ABSENT = "-"
TASK_HEADER = ("task", "state", "pull request", "run")
TASK_COLUMNS = ("task", "state", "pull_request", "run")


def _show(value) -> str:
    return ABSENT if value is None else str(value)


def _render_text(document: dict) -> str:
    rows = [tuple(_show(task[column]) for column in TASK_COLUMNS) for task in document["tasks"]]
    heading = (
        f"wave {document['wave']} of @PROJECT.{document['project']} on {document['branch']},"
        f" started {document['started_at']}, last event {document['last_event']}"
    )
    return "\n".join([heading, render_table(TASK_HEADER, rows)])


def _read_request(options):
    return options


def _decide_exit_code(document: dict) -> int:
    return 0


def _describe_task(events: tuple, states: dict[str, str], wave: str, task: str) -> dict:
    opened = find_last_task_event(events, TaskPrOpened, wave, task)
    finished = find_last_task_event(events, RunFinished, wave, task)
    return {
        "task": task,
        "state": states.get(task),
        "pull_request": None if opened is None else opened.pr,
        "run": None if finished is None else finished.run,
    }


def wave_show(request, runtime: Runtime) -> dict:
    entries = read_ledger(runtime.paths.state_root).entries
    summary = require_wave_summary(entries, request.wave)
    events = tuple(entry.event for entry in entries)
    started = summary.started
    states = read_task_states(runtime.paths.state_root, started.wave)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "wave": started.wave,
        "project": started.project,
        "branch": started.branch,
        "started_at": format_instant(summary.started_at),
        "last_event": summary.last_event,
        "tasks": [_describe_task(events, states, started.wave, task) for task in started.tasks],
    }


COMMAND = Command(
    path=("wave", "show"),
    help="print a wave and each of its tasks with its state, its pull request and its run",
    arguments=(Argument(("wave",), {"help": "the name of a wave of the ledger"}),),
    run=wave_show,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
