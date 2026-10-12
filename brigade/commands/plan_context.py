from pathlib import Path

from brigade.command import Argument, Command
from brigade.errors import BrigadeError
from brigade.planning.assemble_plan_context import assemble_plan_context
from brigade.planning.read_planning_request import read_planning_request
from brigade.registry.find_project import find_project
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_projects import read_projects
from brigade.runtime import Runtime

DOCUMENT_SCHEMA_VERSION = 1
COLUMN_GAP = "  "


def _render_status(document: dict) -> list[str]:
    type_width = max(len(row["type"]) for row in document["status"])
    total_width = max(len(str(row["total"])) for row in document["status"])
    return [
        f"{row['type']:<{type_width}}{COLUMN_GAP}{row['total']:<{total_width}}{COLUMN_GAP}"
        f"{', '.join(f'{status} {count}' for status, count in row['counts'].items())}".rstrip()
        for row in document["status"]
    ]


def _render_anchors(anchors: dict) -> list[str]:
    return [
        line
        for file, entries in anchors.items()
        for line in (file, *(f"  {entry['entity']}{COLUMN_GAP}{entry['anchor']}" for entry in entries))
    ]


def _render_section(lines: list[str]) -> str:
    return "".join(f"{line}\n" for line in lines)


def _render_text(document: dict) -> str:
    request = document["request"]
    sections = [
        _render_section([f"@REQUEST.{request['name']} of @PROJECT.{request['project']}", request["text"]]),
        _render_section([f"Corpus {document['corpus']}", *_render_status(document)]),
        _render_section(
            [
                "Active decisions",
                *(f"@DECISION.{decision['name']}{COLUMN_GAP}{decision['title']}" for decision in document["decisions"]),
            ]
        ),
        _render_section(
            [
                "Draft and todo tasks",
                *(
                    f"@TASK.{task['name']}{COLUMN_GAP}{task['status']}{COLUMN_GAP}{task['title']}"
                    for task in document["tasks"]
                ),
            ]
        ),
        _render_section([f"Next free task number {document['next_task_number']}"]),
        _render_section(["Anchors by file", *_render_anchors(document["anchors"])]),
        *(_render_section([f"Missing schema {entity_type}"]) for entity_type in document["missing"]),
        "\n".join(document["schemas"].values()),
    ]
    return "\n".join(sections).removesuffix("\n")


def _read_request(options):
    return options


def _decide_exit_code(document: dict) -> int:
    return 0


def plan_context(request, runtime: Runtime) -> dict:
    planning_request = read_planning_request(runtime, request.request)
    project = find_project(read_projects(runtime), planning_request.project)
    if read_project_field(project, "CORPUS") is None:
        raise BrigadeError(f"@PROJECT.{project.name} declares no corpus")
    root = Path(read_project_field(project, "PATH"))
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "request": {"name": planning_request.name, "project": project.name, "text": planning_request.text},
        "corpus": str(root),
        **assemble_plan_context(runtime.run_process, root),
    }


COMMAND = Command(
    path=("plan", "context"),
    help="print the package a planner reads to cut a request into a wave",
    group_help="plan the waves of the registered projects",
    arguments=(Argument(("request",)),),
    run=plan_context,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
