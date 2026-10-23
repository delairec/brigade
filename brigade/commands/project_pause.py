import argparse

from brigade.command import Argument, Command
from brigade.registry.change_project_status import change_project_status
from brigade.runtime import Runtime

STATUS = "paused"


def _render_text(document: dict) -> str:
    target = f"@PROJECT.{document['project']}"
    if document["changed"]:
        return f"paused {target}"
    return f"{target} is already {document['status']}"


def project_pause(request: argparse.Namespace, runtime: Runtime) -> dict:
    return change_project_status(runtime, request.name, STATUS)


COMMAND = Command(
    path=("project", "pause"),
    help="pause a project",
    group_help="register the projects brigade works on, list and show them",
    arguments=(Argument(("name",)),),
    run=project_pause,
    render_text=_render_text,
)
