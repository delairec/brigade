import argparse
from pathlib import Path

from brigade.command import Command
from brigade.runtime import Runtime
from brigade.system.check_places import locate_checks
from brigade.system.list_checks import list_checks
from brigade.system.render_table import render_table

DOCUMENT_SCHEMA_VERSION = 1
HEADER = ("name", "source")


def _render_text(document: dict) -> str:
    return render_table(HEADER, [(check["name"], check["source"]) for check in document["checks"]])


def check_list(request: argparse.Namespace, runtime: Runtime) -> dict:
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "checks": list_checks(locate_checks(Path.cwd(), runtime.paths)),
    }


COMMAND = Command(
    path=("check", "list"),
    help="list every check found, its name and its source",
    group_help="list the checks a preflight resolves",
    run=check_list,
    render_text=_render_text,
)
