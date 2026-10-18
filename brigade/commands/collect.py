import json
from datetime import date, datetime, timedelta
from pathlib import Path

from brigade.collecting.collect_document import CollectionRequest, collect_document
from brigade.collecting.collector_environment import CollectorInputs
from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.command import Argument, Command
from brigade.commands._read_forge_environment import FORGE_KIND, FORGE_NAME
from brigade.runtime import Runtime
from brigade.system.collector_places import locate_collectors
from brigade.system.read_optional_configuration import read_optional_configuration
from brigade.system.read_since import read_since

DOCUMENT_SCHEMA_VERSION = 1
COLLECTOR_KIND = "collector"
PARAMETER_SEPARATOR = "="
OPTION_PREFIX = "-"
BEGINNING = date(1970, 1, 1)
DOCUMENT_ROW = "document"
COLUMN_GAP = 2


def _accept_parameter(argument: str) -> bool:
    return PARAMETER_SEPARATOR in argument and not argument.startswith(OPTION_PREFIX)


def _read_request(options):
    return options


def _read_parameters(arguments: list[str]) -> dict:
    return dict(argument.split(PARAMETER_SEPARATOR, 1) for argument in arguments)


def _resolve_since_day(since: timedelta | date | None, now: datetime) -> date:
    if since is None:
        return BEGINNING
    if isinstance(since, timedelta):
        return (now - since).date()
    return since


def _render_value(value) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value)


def _render_text(document: dict) -> str:
    origin = "from cache" if document["cached"] else "collected"
    rows = [
        *((key, _render_value(value)) for key, value in document["summary"].items()),
        (DOCUMENT_ROW, document["document"]),
    ]
    width = max(len(key) for key, _ in rows) + COLUMN_GAP
    return "\n".join([f"{document['collector']} {origin}", *(f"{key:<{width}}{value}" for key, value in rows)])


def _decide_exit_code(document: dict) -> int:
    return 0


def collect(request, runtime: Runtime) -> dict:
    project = Path.cwd()
    collector = runtime.resolve_plugin(COLLECTOR_KIND, request.name, places=locate_collectors(project, runtime.paths))
    inputs = CollectorInputs(
        project=project,
        since=_resolve_since_day(request.since, runtime.now),
        parameters=_read_parameters(request.extra_arguments),
    )
    collection = collect_document(
        collector,
        CollectionRequest(
            inputs=inputs,
            refresh=request.refresh,
            equipment=CollectorEquipment(
                configuration=read_optional_configuration(runtime.paths.configuration_file),
                forge=runtime.resolve_plugin(FORGE_KIND, FORGE_NAME),
                forge_name=FORGE_NAME,
            ),
        ),
        runtime,
    )
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "collector": collector.name,
        "source": collector.source,
        "cached": collection.cached,
        "summary": collection.document["summary"],
        "document": str(collection.document_path),
    }


COMMAND = Command(
    path=("collect",),
    help="run a collector and print the summary and the path of its document; key=value pairs are its parameters",
    arguments=(
        Argument(("name",), {"help": "the name of the collector"}),
        Argument(
            ("--since",), {"type": read_since, "help": "<n>d or a day YYYY-MM-DD in UTC, the beginning by default"}
        ),
        Argument(("--refresh",), {"action": "store_true", "help": "ignore the cache and replace its entry"}),
    ),
    run=collect,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
    accept_extra_argument=_accept_parameter,
)
