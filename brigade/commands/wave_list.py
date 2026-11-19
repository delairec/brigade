import argparse

from brigade.command import Argument, Command
from brigade.ledger.format_instant import format_instant
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.pr_merged import PrMerged
from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.run_finished import RunFinished
from brigade.ledger.sum_reported import sum_reported
from brigade.runtime import Runtime
from brigade.system.render_table import render_table
from brigade.waves.read_task_states import read_task_states
from brigade.waves.read_wave_pause import read_wave_pause
from brigade.waves.summarize_waves import ENDING_EVENTS, WaveSummary, summarize_waves

DOCUMENT_SCHEMA_VERSION = 1
HEADER = ("wave", "project", "branch", "last event", "tasks")
COLUMNS = ("wave", "project", "branch", "last_event", "tasks")
NO_ROUND = 0


def _render_text(document: dict) -> str:
    return render_table(HEADER, [tuple(str(row[column]) for column in COLUMNS) for row in document["waves"]])


def _is_ended(summary: WaveSummary) -> bool:
    return not summary.is_open


def _of_wave(entries: tuple[LedgerEntry, ...], wave: str) -> list[LedgerEntry]:
    return [entry for entry in entries if getattr(entry.event, "wave", None) == wave]


def _find_ended_at(entries: list[LedgerEntry]) -> str | None:
    ended = [entry.instant for entry in entries if isinstance(entry.event, ENDING_EVENTS)]
    return format_instant(ended[0]) if ended else None


def _describe_halt(entries: list[LedgerEntry], summary: WaveSummary) -> dict | None:
    pause = read_wave_pause(tuple(entry.event for entry in entries), summary.started.wave)
    if pause is None or not summary.is_open:
        return None
    return pause.to_document()


def _describe(entries: tuple[LedgerEntry, ...], summary: WaveSummary) -> dict:
    started = summary.started
    of_wave = _of_wave(entries, started.wave)
    states = read_task_states(entries, started.wave)
    events = [entry.event for entry in of_wave]
    return {
        "wave": started.wave,
        "project": started.project,
        "branch": started.branch,
        "last_event": summary.last_event,
        "tasks": len(started.tasks),
        "started_at": format_instant(summary.started_at),
        "ended_at": _find_ended_at(of_wave),
        "task_states": [{"task": task, "state": states.get(task)} for task in started.tasks],
        "halt": _describe_halt(of_wave, summary),
        "rounds": max((event.rounds for event in events if isinstance(event, PrMerged)), default=NO_ROUND),
        "cost_usd": sum_reported(event.cost_usd for event in events if isinstance(event, RunFinished)),
    }


def wave_list(request: argparse.Namespace, runtime: Runtime) -> dict:
    entries = read_ledger(runtime.paths.state_root).entries
    summaries = sorted(summarize_waves(entries), key=_is_ended)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "waves": [
            _describe(entries, summary) for summary in summaries if request.project in (None, summary.started.project)
        ],
    }


COMMAND = Command(
    path=("wave", "list"),
    help="print one row per wave of the ledger, the open waves first",
    arguments=(Argument(("--project",), {"help": "only the waves of this registered project"}),),
    run=wave_list,
    render_text=_render_text,
)
