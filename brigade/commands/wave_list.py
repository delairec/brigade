from brigade.command import Argument, Command
from brigade.corpus.read_entities import read_entities
from brigade.ledger.read_ledger import read_ledger
from brigade.registry.require_operational_corpus import require_operational_corpus
from brigade.runtime import Runtime
from brigade.system.render_table import render_table
from brigade.waves.describe_request import describe_request
from brigade.waves.find_wave_name import find_wave_name
from brigade.waves.read_wave_request import ENTITY_TYPE

DOCUMENT_SCHEMA_VERSION = 1
ABSENT = "-"
HEADER = ("request", "project", "status", "wave", "milestone", "branch", "created at")
COLUMNS = ("name", "project", "status", "wave", "milestone", "branch", "created_at")


def _show(value) -> str:
    return ABSENT if value is None else value


def _render_text(document: dict) -> str:
    return render_table(HEADER, [tuple(_show(row[column]) for column in COLUMNS) for row in document["requests"]])


def _read_request(options):
    return options


def _decide_exit_code(document: dict) -> int:
    return 0


def wave_list(request, runtime: Runtime) -> dict:
    require_operational_corpus(runtime.paths)
    events = tuple(entry.event for entry in read_ledger(runtime.paths.state_root).entries)
    described = [
        describe_request(entity)
        for entity in read_entities(runtime.run_process, runtime.paths.config_root, ENTITY_TYPE)
    ]
    rows = [{**row, "wave": find_wave_name(events, row["project"], row["branch"])} for row in described]
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "requests": [
            {column: row[column] for column in COLUMNS} for row in rows if request.project in (None, row["project"])
        ],
    }


COMMAND = Command(
    path=("wave", "list"),
    help="print one row per request",
    arguments=(Argument(("--project",), {"help": "only the requests of this registered project"}),),
    run=wave_list,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
