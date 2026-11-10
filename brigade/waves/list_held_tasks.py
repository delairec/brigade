from dataclasses import dataclass

from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.task_parked import TaskParked
from brigade.ledger.wave_started import WaveStarted
from brigade.tasks.digest_task_entity import digest_task_entity
from brigade.waves.find_last_task_event import find_last_task_event
from brigade.waves.is_task_todo_of_reading import is_task_todo_of_reading
from brigade.waves.read_parked_question import read_parked_question
from brigade.waves.read_project_tasks import ProjectTasks
from brigade.waves.read_task_state import TASK_EVENTS
from brigade.waves.summarize_waves import WaveSummary, summarize_waves

NO_RECORDED_DIGEST = {}
NO_QUESTION = None
LINE_BREAK = "\n"


@dataclass(frozen=True)
class HeldTask:
    task: str
    wave: str
    question: str


def _map_latest_waves(entries: tuple[LedgerEntry, ...], project: str) -> dict[str, WaveSummary]:
    return {
        task: summary
        for summary in summarize_waves(entries)
        if summary.started.project == project
        for task in summary.started.tasks
    }


def _read_recorded_digest(started: WaveStarted, task: str) -> str | None:
    return (started.task_digests or NO_RECORDED_DIGEST).get(task)


def _is_holdable(task: str, summary: WaveSummary, tasks: ProjectTasks) -> bool:
    entity = tasks.by_name.get(task)
    return (
        entity is not None
        and is_task_todo_of_reading(tasks, entity)
        and not summary.is_open
        and digest_task_entity(entity) == _read_recorded_digest(summary.started, task)
    )


def _read_question_of_last_park(events: tuple, summary: WaveSummary, task: str) -> str | None:
    last_event = find_last_task_event(events, TASK_EVENTS, summary.started.wave, task)
    return read_parked_question(last_event.reason) if isinstance(last_event, TaskParked) else NO_QUESTION


def list_held_tasks(entries: tuple[LedgerEntry, ...], project: str, tasks: ProjectTasks) -> tuple[HeldTask, ...]:
    events = tuple(entry.event for entry in entries)
    latest_waves = _map_latest_waves(entries, project)
    questions = {
        task: _read_question_of_last_park(events, summary, task)
        for task, summary in latest_waves.items()
        if _is_holdable(task, summary, tasks)
    }
    return tuple(
        HeldTask(task=task, wave=latest_waves[task].started.wave, question=question.partition(LINE_BREAK)[0])
        for task, question in questions.items()
        if question is not None
    )
