import argparse

from brigade.command import Argument, Command
from brigade.corpus.read_entities import read_entities
from brigade.registry.require_operational_corpus import require_operational_corpus
from brigade.runtime import Runtime
from brigade.system.render_table import render_table
from brigade.waves.describe_request import describe_request
from brigade.waves.read_wave_request import ENTITY_TYPE

DOCUMENT_SCHEMA_VERSION = 1
ABSENT = "-"
HEADER = ("request", "project", "status", "milestone", "pr", "created at")
COLUMNS = ("name", "project", "status", "milestone", "pr", "created_at")


def _show(value) -> str:
    return ABSENT if value is None else str(value)


def _render_text(document: dict) -> str:
    return render_table(HEADER, [tuple(_show(row[column]) for column in COLUMNS) for row in document["requests"]])


def request_list(request: argparse.Namespace, runtime: Runtime) -> dict:
    require_operational_corpus(runtime.paths)
    rows = [
        describe_request(entity)
        for entity in read_entities(runtime.run_process, runtime.paths.config_root, ENTITY_TYPE)
    ]
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "requests": [
            {column: row[column] for column in COLUMNS} for row in rows if request.project in (None, row["project"])
        ],
    }


COMMAND = Command(
    path=("request", "list"),
    help="print one row per request",
    arguments=(Argument(("--project",), {"help": "only the requests of this registered project"}),),
    run=request_list,
    render_text=_render_text,
)
