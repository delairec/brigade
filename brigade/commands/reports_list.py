import argparse

from brigade.command import Command
from brigade.reports.read_reports import read_reports
from brigade.runtime import Runtime
from brigade.system.render_table import render_table

DOCUMENT_SCHEMA_VERSION = 1
DOCUMENT_KIND = "document"
OPERATIONAL_CORPUS_DOCUMENT = "awawa"
HEADER = ("id", "kind", "project")
NO_PROJECT = "-"
NO_REPORT = "no report"


def _render_text(document: dict) -> str:
    reports = document["reports"]
    if not reports:
        return NO_REPORT
    return render_table(HEADER, [(report["id"], report["kind"], report["project"] or NO_PROJECT) for report in reports])


def reports_list(request: argparse.Namespace, runtime: Runtime) -> dict:
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "reports": [
            {column: report[column] for column in HEADER}
            for report in read_reports(runtime, runtime.resolve_plugin(DOCUMENT_KIND, OPERATIONAL_CORPUS_DOCUMENT))
        ],
    }


COMMAND = Command(
    path=("reports", "list"),
    help="print one row per wave report and study answer",
    run=reports_list,
    render_text=_render_text,
)
