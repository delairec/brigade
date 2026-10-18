from brigade.command import Argument, Command
from brigade.ledger.read_ledger import read_ledger
from brigade.registry.read_project_field import read_project_field
from brigade.runtime import Runtime
from brigade.system.read_optional_configuration import read_optional_configuration
from brigade.system.render_table import render_table
from brigade.waves.decide_waits_for import decide_waits_for
from brigade.waves.describe_request import describe_request
from brigade.waves.find_last_task_run import find_last_task_run
from brigade.waves.find_wave_name import find_wave_name
from brigade.waves.list_wave_tasks import list_wave_tasks
from brigade.waves.read_wave_request import read_wave_request

DOCUMENT_SCHEMA_VERSION = 1
ABSENT = "-"
NO_RUN = ""
FIELD_NAME_WIDTH = 12
DESCRIBED_FIELDS = (("wave", "wave"), ("milestone", "milestone"), ("branch", "branch"), ("created at", "created_at"))
TASK_HEADER = ("task", "state", "run", "pull request", "title")


def _show(value) -> str:
    return ABSENT if value is None else str(value)


def _render_text(document: dict) -> str:
    fields = [*DESCRIBED_FIELDS, ("waits for", "waits_for")]
    rows = [
        (task["task"], task["state"], task["run"] or NO_RUN, _show(task["pull_request"]), task["title"])
        for task in document["tasks"]
    ]
    return "\n".join(
        [
            f"@REQUEST.{document['request']} of @PROJECT.{document['project']}  {document['status']}",
            document["text"],
            *(f"{label:<{FIELD_NAME_WIDTH}}{_show(document[key])}" for label, key in fields),
            "",
            render_table(TASK_HEADER, rows),
        ]
    )


def _read_request(options):
    return options


def _decide_exit_code(document: dict) -> int:
    return 0


def wave_show(request, runtime: Runtime) -> dict:
    entity = read_wave_request(runtime, request.request)
    request_fields = describe_request(entity)
    events = tuple(entry.event for entry in read_ledger(runtime.paths.state_root).entries)
    described = {
        **request_fields,
        "wave": find_wave_name(events, request_fields["project"], request_fields["branch"]),
    }
    configuration = read_optional_configuration(runtime.paths.configuration_file)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "request": described["name"],
        "project": described["project"],
        "text": read_project_field(entity, "TEXT"),
        "status": described["status"],
        "wave": described["wave"],
        "milestone": described["milestone"],
        "branch": described["branch"],
        "created_at": described["created_at"],
        "waits_for": decide_waits_for(runtime, described),
        "tasks": [
            {**listed, "run": find_last_task_run(events, described["project"], listed["task"])}
            for listed in list_wave_tasks(runtime, configuration, described)
        ],
    }


COMMAND = Command(
    path=("wave", "show"),
    help="print a request and the tasks of its wave with their states",
    arguments=(Argument(("request",), {"help": "the name of a REQUEST"}),),
    run=wave_show,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
