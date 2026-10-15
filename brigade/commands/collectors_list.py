from pathlib import Path

from brigade.command import Command
from brigade.runtime import Runtime
from brigade.system.collector_places import locate_collectors
from brigade.system.list_collectors import list_collectors
from brigade.system.render_table import render_table

DOCUMENT_SCHEMA_VERSION = 1
HEADER = ("name", "source")


def _read_request(options):
    return options


def _render_text(document: dict) -> str:
    return render_table(HEADER, [(collector["name"], collector["source"]) for collector in document["collectors"]])


def _decide_exit_code(document: dict) -> int:
    return 0


def collectors_list(request, runtime: Runtime) -> dict:
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "collectors": list_collectors(locate_collectors(Path.cwd(), runtime.paths)),
    }


COMMAND = Command(
    path=("collectors", "list"),
    help="list every collector found, its name and its source",
    group_help="list the collectors brigade collect resolves",
    run=collectors_list,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
