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


def _read_project(event) -> str | None:
    return getattr(event, PROJECT_ATTRIBUTE, None)


def collect(environment: dict, runtime: Runtime, equipment: CollectorEquipment) -> dict:
    inputs = read_collector_environment(environment)
    start = datetime.combine(inputs.since, time(), tzinfo=UTC)
    project = find_project_at(read_projects(runtime), inputs.project)
    entries = [
        entry
        for entry in read_ledger(runtime.paths.state_root).entries
        if entry.instant >= start and (project is None or _read_project(entry.event) == project.name)
    ]
    items = [
        {"ts": format_instant(entry.instant), "event": entry.event.name, "project": _read_project(entry.event)}
        for entry in entries
    ]
    summary = {
        "events": dict(Counter(entry.event.name for entry in entries)),
        "outcomes": dict(Counter(entry.event.outcome for entry in entries if entry.event.name == RunFinished.name)),
    }
    return describe_collection(NAME, runtime, summary, items)
