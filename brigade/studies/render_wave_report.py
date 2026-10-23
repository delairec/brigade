import json
from dataclasses import dataclass

from brigade.corpus.quote_awawa_string import quote_awawa_string

ANSWER_TYPE = "REPORT"
WAVE_STARTED = "wave.started"
TASK_STATE = "task.state"
TASK_PARKED = "task.parked"
RUN_FINISHED = "run.finished"
MERGED_STATE = "merged"
PARKED_STATE = "parked"
SPEC_FIELD = "SPEC"
AFTER_FIELD = "AFTER"
TASK_REFERENCE_PREFIX = "@TASK."


@dataclass(frozen=True)
class WaveEvidence:
    wave: str
    project: str
    corpus_folder: str
    events: list[dict]
    pull_requests: list[dict]
    tasks: list[dict]
    changes: list[dict]


def _read_wave_tasks(events: list[dict]) -> list[str]:
    return next(event["tasks"] for event in events if event["event"] == WAVE_STARTED)


def _read_last_states(events: list[dict]) -> dict[str, str]:
    return {event["task"]: event["state"] for event in events if event["event"] == TASK_STATE}


def _read_text(field: dict) -> str:
    return "".join(json.loads(atom) for atom in field["atoms"])


def _read_predecessors(task: dict) -> list[str]:
    return [
        field["atoms"][0].removeprefix(TASK_REFERENCE_PREFIX)
        for field in task["fields"]
        if field["name"] == AFTER_FIELD
    ]


def _render_task_row(task: str, state: str, pull_requests: list[dict]) -> str:
    numbers = [f"#{pull_request['number']}" for pull_request in pull_requests if pull_request["task"] == task]
    return " ".join([task, state, *numbers])


def _count_statistics(evidence: WaveEvidence, wave_tasks: list, states: dict, merged: list) -> dict:
    return {
        "tasks": len(wave_tasks),
        "merged": len(merged),
        "parked": sum(states.get(task) == PARKED_STATE for task in wave_tasks),
        "runs": sum(event["event"] == RUN_FINISHED for event in evidence.events),
        "files": len(evidence.changes),
        "insertions": sum(change["insertions"] for change in evidence.changes),
        "deletions": sum(change["deletions"] for change in evidence.changes),
    }


def _render_findings(evidence: WaveEvidence, wave_tasks: list, merged: list) -> list[tuple[str, str]]:
    return [
        *[
            ("GRAPH", f"{task['name']} after {predecessor}")
            for task in evidence.tasks
            for predecessor in _read_predecessors(task)
            if predecessor in wave_tasks
        ],
        *[
            ("MANUAL_TEST", f"{task['name']}: {_read_text(field)}")
            for task in evidence.tasks
            if task["name"] in merged
            for field in task["fields"]
            if field["name"] == SPEC_FIELD
        ],
        *[
            ("INSTRUCTIONS_CHANGE", f"{change['path']} +{change['insertions']} -{change['deletions']}")
            for change in evidence.changes
            if change["path"].startswith(f"{evidence.corpus_folder}/")
        ],
        *[
            ("PARKED_QUESTION", f"{event['task']} blocked by {blocker}")
            for event in evidence.events
            if event["event"] == TASK_PARKED
            for blocker in event["blockers"]
        ],
    ]


def _render_rows(evidence: WaveEvidence) -> list[tuple[str, str]]:
    wave_tasks = _read_wave_tasks(evidence.events)
    states = _read_last_states(evidence.events)
    merged = [task for task in wave_tasks if states.get(task) == MERGED_STATE]
    statistics = _count_statistics(evidence, wave_tasks, states, merged)
    return [
        ("WAVE", evidence.wave),
        ("PROJECT", evidence.project),
        *[("TASK_ROW", _render_task_row(task, states[task], evidence.pull_requests)) for task in wave_tasks],
        *[("STATISTIC", f"{name} {value}") for name, value in statistics.items()],
        *_render_findings(evidence, wave_tasks, merged),
    ]


def render_wave_report(evidence: WaveEvidence) -> str:
    lines = [f"{ANSWER_TYPE} {evidence.wave}"]
    lines.extend(f"\t{name} {quote_awawa_string(value)}" for name, value in _render_rows(evidence))
    return "\n".join(lines) + "\n"
