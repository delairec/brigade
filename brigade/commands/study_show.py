from brigade.command import Argument, Command
from brigade.runtime import Runtime
from brigade.studies.describe_last_study_order import describe_last_study_order
from brigade.studies.read_last_study_orders import read_last_study_orders
from brigade.studies.read_study_entity import read_study_entity

DOCUMENT_SCHEMA_VERSION = 1
FIELD_NAME_WIDTH = 12
NO_VALUE = "-"


def _present(value: str | None) -> str:
    return NO_VALUE if value is None else value


def _render_text(document: dict) -> str:
    study = document["study"]
    lines = [
        f"@STUDY.{study['name']}",
        *(f"{field['name']:<{FIELD_NAME_WIDTH}}{field['value']}" for field in study["fields"]),
        f"{'last run':<{FIELD_NAME_WIDTH}}{_present(study['last_run'])}",
        f"{'outcome':<{FIELD_NAME_WIDTH}}{_present(study['outcome'])}",
    ]
    return "\n".join(lines)


def _read_request(options):
    return options


def _decide_exit_code(document: dict) -> int:
    return 0


def study_show(request, runtime: Runtime) -> dict:
    entity = read_study_entity(runtime, request.name)
    last_order = read_last_study_orders(runtime.paths.state_root).get(entity.name)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "study": {
            "name": entity.name,
            "fields": [{"name": field.name, "value": field.value} for field in entity.fields],
            **describe_last_study_order(last_order),
        },
    }


COMMAND = Command(
    path=("study", "show"),
    help="print the fields of a study, its last run and its outcome",
    arguments=(Argument(("name",)),),
    run=study_show,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
