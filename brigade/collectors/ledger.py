from collections import Counter
from datetime import UTC, datetime, time

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.collecting.describe_collection import describe_collection
from brigade.collecting.read_collector_environment import read_collector_environment
from brigade.ledger.format_instant import format_instant
from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.run_finished import RunFinished
from brigade.registry.find_project_at import find_project_at
from brigade.registry.read_projects import read_projects
from brigade.runtime import Runtime

NAME = "ledger"
PROJECT_ATTRIBUTE = "project"
WAVE_ATTRIBUTE = "wave"
WAVE_PARAMETER = "wave"


def _read_project(event) -> str | None:
    return getattr(event, PROJECT_ATTRIBUTE, None)


def _select_by_project(inputs, runtime: Runtime):
    project = find_project_at(read_projects(runtime), inputs.project)
    return lambda event: project is None or _read_project(event) == project.name


def _select_by_wave(wave: str):
    return lambda event: getattr(event, WAVE_ATTRIBUTE, None) == wave


def collect(environment: dict, runtime: Runtime, equipment: CollectorEquipment) -> dict:
    inputs = read_collector_environment(environment)
    start = datetime.combine(inputs.since, time(), tzinfo=UTC)
    if WAVE_PARAMETER in inputs.parameters:
        is_selected = _select_by_wave(inputs.parameters[WAVE_PARAMETER])
    else:
        is_selected = _select_by_project(inputs, runtime)
    entries = [
        entry
        for entry in read_ledger(runtime.paths.state_root).entries
        if entry.instant >= start and is_selected(entry.event)
    ]
    items = [
        {"ts": format_instant(entry.instant), "event": entry.event.name, **entry.event.to_document()}
        for entry in entries
    ]
    summary = {
        "events": dict(Counter(entry.event.name for entry in entries)),
        "outcomes": dict(Counter(entry.event.outcome for entry in entries if entry.event.name == RunFinished.name)),
    }
    return describe_collection(NAME, runtime, summary, items)
