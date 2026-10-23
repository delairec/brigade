from pathlib import Path

from brigade.collecting.find_absence import find_absence
from brigade.command import Command
from brigade.corpus.read_entities import Entity
from brigade.registry.find_project_at import find_project_at
from brigade.registry.read_projects import read_projects
from brigade.runtime import Runtime
from brigade.system.collector_places import BUILT_IN_SOURCE, locate_collectors
from brigade.system.list_collectors import list_collectors
from brigade.system.render_table import render_table

DOCUMENT_SCHEMA_VERSION = 1
HEADER = ("name", "source", "absent")
PRESENT = "-"


def _render_text(document: dict) -> str:
    return render_table(
        HEADER,
        [
            (collector["name"], collector["source"], collector["absent"] or PRESENT)
            for collector in document["collectors"]
        ],
    )


def _find_current_project(runtime: Runtime) -> Entity | None:
    if not runtime.paths.schema_file.exists():
        return None
    return find_project_at(read_projects(runtime), Path.cwd())


def _describe_collector(collector: dict, project: Entity | None) -> dict:
    absence = find_absence(collector["name"], project) if collector["source"] == BUILT_IN_SOURCE else None
    return {**collector, "absent": absence}


def collectors_list(request, runtime: Runtime) -> dict:
    project = _find_current_project(runtime)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "collectors": [
            _describe_collector(collector, project)
            for collector in list_collectors(locate_collectors(Path.cwd(), runtime.paths))
        ],
    }


COMMAND = Command(
    path=("collectors", "list"),
    help="list every collector found, its name and its source",
    group_help="list the collectors brigade collect resolves",
    run=collectors_list,
    render_text=_render_text,
)
