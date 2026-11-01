from datetime import datetime

from brigade.errors import BrigadeError
from brigade.ledger.finished_run import FinishedRun
from brigade.ledger.format_instant import format_instant
from brigade.ledger.group_runs import group_runs
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.pr_merged import PrMerged
from brigade.ledger.read_ledger import LedgerReading
from brigade.ledger.run_finished import RunFinished
from brigade.ledger.sum_reported import sum_reported
from brigade.ledger.sum_token_usage import sum_token_usage
from brigade.ledger.summarize_measure import summarize_measure
from brigade.ledger.task_parked import TaskParked
from brigade.ledger.wave_paused import WavePaused
from brigade.ledger.wave_resumed import WaveResumed
from brigade.waves.count_repair_rounds import count_repair_rounds

FIRST_HAND_OVER_SEGMENT = 2
MILLISECONDS_PER_SECOND = 1000


def _measure_ms(start: datetime, end: datetime) -> int:
    return int((end - start).total_seconds() * MILLISECONDS_PER_SECOND)


def _list_tasks(events: list) -> list[str]:
    return list(dict.fromkeys(event.task for event in events if getattr(event, "task", None) is not None))


def _summarize_by(runs: list[FinishedRun], attribute: str) -> dict:
    names = sorted({getattr(run.last, attribute) for run in runs}, key=str)
    return {
        name: summarize_measure([run for run in runs if getattr(run.last, attribute) == name], "main_steps")
        for name in names
    }


def _pair_pauses(entries: list[LedgerEntry]) -> list[dict]:
    pauses = []
    paused_at = None
    for entry in entries:
        if isinstance(entry.event, WavePaused) and paused_at is None:
            paused_at = entry.instant
        elif isinstance(entry.event, WaveResumed) and paused_at is not None:
            pauses.append(
                {
                    "paused_at": format_instant(paused_at),
                    "resumed_at": format_instant(entry.instant),
                    "duration_ms": _measure_ms(paused_at, entry.instant),
                }
            )
            paused_at = None
    if paused_at is not None:
        pauses.append({"paused_at": format_instant(paused_at), "resumed_at": None, "duration_ms": None})
    return pauses


def _list_merged_pull_requests(events: list) -> list[dict]:
    return [
        {"task": event.task, "pr": event.pr, "rounds": event.rounds} for event in events if isinstance(event, PrMerged)
    ]


def _list_hand_overs(events: list) -> list[dict]:
    return [
        {"task": event.task, "role": event.role, "slot": event.slot, "segment": event.segment}
        for event in events
        if isinstance(event, RunFinished) and event.segment >= FIRST_HAND_OVER_SEGMENT
    ]


def _list_runs(events: list) -> tuple[dict, ...]:
    return tuple(
        {"slot": event.slot, "wave": event.wave, "task": event.task, "run": event.run}
        for event in events
        if isinstance(event, RunFinished)
    )


def _sum_steps_by_task(events: list) -> dict:
    steps = {}
    for event in events:
        if isinstance(event, RunFinished) and event.task is not None and event.main_steps is not None:
            steps[event.task] = steps.get(event.task, 0) + event.main_steps
    return steps


def _cost_task(task: str, runs: list[FinishedRun]) -> dict:
    task_runs = [run for run in runs if run.last.task == task]
    segments = [segment for run in task_runs for segment in run.segments]
    steps = [run.main_steps for run in task_runs]
    return {
        "task": task,
        "steps": sum_reported(measure.value for measure in steps),
        "partial": any(measure.partial for measure in steps),
        "duration_ms": sum_reported(segment.duration_ms for segment in segments),
        "cost_usd": sum_reported(segment.cost_usd for segment in segments),
    }


def _sum_usage(runs: list[RunFinished]) -> dict | None:
    usage = sum_token_usage(run.usage for run in runs)
    return None if usage is None else usage.to_document()


def _cost_wave(events: list, runs: list[FinishedRun], tasks: list[str]) -> dict:
    finished = [event for event in events if isinstance(event, RunFinished)]
    return {
        "cost_usd": sum_reported(run.cost_usd for run in finished),
        "usage": _sum_usage(finished),
        "by_task": [_cost_task(task, runs) for task in tasks],
    }


def _date_entries(entries: list[LedgerEntry]) -> list[dict]:
    return [
        {"at": format_instant(entry.instant), "event": entry.event.name, "fields": entry.event.to_document()}
        for entry in sorted(entries, key=lambda entry: entry.instant)
    ]


def describe_wave(reading: LedgerReading, wave: str) -> dict:
    entries = [entry for entry in reading.entries if getattr(entry.event, "wave", None) == wave]
    if not entries:
        raise BrigadeError(f"no event names the wave {wave}")
    events = [entry.event for entry in entries]
    first = min(entry.instant for entry in entries)
    last = max(entry.instant for entry in entries)
    runs = group_runs(entries)
    pauses = _pair_pauses(entries)
    tasks = _list_tasks(events)
    return {
        "view": "wave",
        "wave": wave,
        "first": format_instant(first),
        "last": format_instant(last),
        "wall_time_ms": _measure_ms(first, last),
        "tasks": tasks,
        **_cost_wave(events, runs, tasks),
        "pull_requests": _list_merged_pull_requests(events),
        "steps": {"by_slot": _summarize_by(runs, "slot"), "by_role": _summarize_by(runs, "role")},
        "pauses": pauses,
        "paused_ms": sum(pause["duration_ms"] for pause in pauses if pause["duration_ms"] is not None),
        "hand_overs": _list_hand_overs(events),
        "parked": [event.task for event in events if isinstance(event, TaskParked)],
        "rounds_by_task": count_repair_rounds(tuple(entries), _list_runs(events), wave),
        "steps_by_task": _sum_steps_by_task(events),
        "timeline": _date_entries(entries),
    }
