from brigade.command import Argument, Command
from brigade.registry.change_project_status import change_project_status

STATUS = "paused"


def _read_request(options):
    return options


def _render_text(document: dict) -> str:
    target = f"@PROJECT.{document['project']}"
    if document["changed"]:
        return f"paused {target}"
    return f"{target} is already {document['status']}"


def _decide_exit_code(document: dict) -> int:
    return 0


def project_pause(request, runtime) -> dict:
    return change_project_status(runtime, request.name, STATUS)


COMMAND = Command(
    path=("project", "pause"),
    help="pause a project",
    group_help="register the projects brigade works on, list and show them",
    arguments=(Argument(("name",)),),
    run=project_pause,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
