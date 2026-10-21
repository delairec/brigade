from brigade.command import Argument, Command
from brigade.registry.read_project_field import read_project_field
from brigade.runtime import Runtime
from brigade.waves.describe_request import describe_request
from brigade.waves.read_planner_run import read_planner_run
from brigade.waves.read_wave_request import read_wave_request

DOCUMENT_SCHEMA_VERSION = 1
ABSENT = "-"
FIELD_NAME_WIDTH = 12
DESCRIBED_FIELDS = (("milestone", "milestone"), ("pr", "pr"), ("created at", "created_at"))


def _show(value) -> str:
    return ABSENT if value is None else str(value)


def _show_planner(planner: dict | None) -> str:
    return ABSENT if planner is None else f"{planner['state']}, run {planner['run']}"


def _render_text(document: dict) -> str:
    return "\n".join(
        [
            f"@REQUEST.{document['request']} of @PROJECT.{document['project']}  {document['status']}",
            document["text"],
            *(f"{label:<{FIELD_NAME_WIDTH}}{_show(document[key])}" for label, key in DESCRIBED_FIELDS),
            f"{'planner':<{FIELD_NAME_WIDTH}}{_show_planner(document['planner'])}",
        ]
    )


def _read_request(options):
    return options


def _decide_exit_code(document: dict) -> int:
    return 0


def request_show(request, runtime: Runtime) -> dict:
    entity = read_wave_request(runtime, request.request)
    described = describe_request(entity)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "request": described["name"],
        "project": described["project"],
        "text": read_project_field(entity, "TEXT"),
        "status": described["status"],
        "milestone": described["milestone"],
        "pr": described["pr"],
        "created_at": described["created_at"],
        "planner": read_planner_run(runtime.paths.state_root, described["name"]),
    }


COMMAND = Command(
    path=("request", "show"),
    help="print a request, its status, its plan and its pull request",
    arguments=(Argument(("request",), {"help": "the name of a REQUEST"}),),
    run=request_show,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
