import argparse
from datetime import date, datetime, timedelta
from pathlib import Path

from brigade.collecting.collect_document import CollectionRequest, collect_document
from brigade.collecting.collector_environment import CollectorInputs
from brigade.command import Argument, Command
from brigade.commands._accept_parameter import accept_parameter
from brigade.commands._equip_collector import equip_collector
from brigade.commands._read_parameters import read_parameters
from brigade.runtime import Runtime
from brigade.system.collector_places import locate_collectors
from brigade.system.read_since import read_since
from brigade.system.render_inline_json import render_inline_json

DOCUMENT_SCHEMA_VERSION = 1
COLLECTOR_KIND = "collector"
BEGINNING = date(1970, 1, 1)
DOCUMENT_ROW = "document"
COLUMN_GAP = 2


def _resolve_since_day(since: timedelta | date | None, now: datetime) -> date:
    if since is None:
        return BEGINNING
    if isinstance(since, timedelta):
        return (now - since).date()
    return since


def _render_value(value) -> str:
    if isinstance(value, str):
        return value
    return render_inline_json(value)


def _render_text(document: dict) -> str:
    origin = "from cache" if document["cached"] else "collected"
    rows = [
        *((key, _render_value(value)) for key, value in document["summary"].items()),
        (DOCUMENT_ROW, document["document"]),
    ]
    width = max(len(key) for key, _ in rows) + COLUMN_GAP
    return "\n".join([f"{document['collector']} {origin}", *(f"{key:<{width}}{value}" for key, value in rows)])


def collect(request: argparse.Namespace, runtime: Runtime) -> dict:
    project = Path.cwd()
    collector = runtime.resolve_plugin(COLLECTOR_KIND, request.name, places=locate_collectors(project, runtime.paths))
    inputs = CollectorInputs(
        project=project,
        since=_resolve_since_day(request.since, runtime.now),
        parameters=read_parameters(request.extra_arguments),
    )
    collection = collect_document(
        collector,
        CollectionRequest(
            inputs=inputs,
            refresh=request.refresh,
            equipment=equip_collector(project, runtime),
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
    path=("collector", "run"),
    help="run a collector and print the summary and the path of its document; key=value pairs are its parameters",
    group_help="run a collector and list the collectors it resolves",
    arguments=(
        Argument(("name",), {"help": "the name of the collector"}),
        Argument(
            ("--since",), {"type": read_since, "help": "<n>d or a day YYYY-MM-DD in UTC, the beginning by default"}
        ),
        Argument(("--refresh",), {"action": "store_true", "help": "ignore the cache and replace its entry"}),
    ),
    run=collect,
    render_text=_render_text,
    accept_extra_argument=accept_parameter,
)
