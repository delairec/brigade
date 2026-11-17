import argparse

from brigade.command import Argument, Command
from brigade.errors import BrigadeError
from brigade.reports.read_reports import read_reports
from brigade.reports.render_report_markdown import render_report_markdown
from brigade.runtime import Runtime

DOCUMENT_SCHEMA_VERSION = 1
DOCUMENT_KIND = "progress_form"
OPERATIONAL_CORPUS_DOCUMENT = "awawa"
PATTERN_FIELD = "PATTERN"


def _render_text(document: dict) -> str:
    report = document["report"]
    pattern_fields = [] if report["pattern"] is None else [{"name": PATTERN_FIELD, "value": report["pattern"]}]
    return render_report_markdown(
        {"type": report["type"], "name": report["id"], "fields": [*pattern_fields, *report["fields"]]}
    )


def report_show(request: argparse.Namespace, runtime: Runtime) -> dict:
    report = next(
        (
            report
            for report in read_reports(runtime, runtime.resolve_plugin(DOCUMENT_KIND, OPERATIONAL_CORPUS_DOCUMENT))
            if report["id"] == request.id
        ),
        None,
    )
    if report is None:
        raise BrigadeError(f"no report {request.id}")
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, "report": report}


COMMAND = Command(
    path=("report", "show"),
    help="print a wave, task or milestone report or an order result, rendered from its entity",
    arguments=(Argument(("id",), {"help": "the id of the report, as brigade report list prints it"}),),
    run=report_show,
    render_text=_render_text,
)
