import argparse

from brigade.command import Argument, Command
from brigade.errors import BrigadeError
from brigade.reports.read_reports import read_reports
from brigade.reports.render_report_markdown import render_report_markdown
from brigade.runtime import Runtime

DOCUMENT_SCHEMA_VERSION = 1
DOCUMENT_KIND = "document"
OPERATIONAL_CORPUS_DOCUMENT = "awawa"


def _render_text(document: dict) -> str:
    report = document["report"]
    return render_report_markdown({"type": report["type"], "name": report["id"], "fields": report["fields"]})


def reports_show(request: argparse.Namespace, runtime: Runtime) -> dict:
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
    path=("reports", "show"),
    help="print a wave report or a study answer, rendered from its entity",
    arguments=(Argument(("id",), {"help": "the id of the report, as brigade reports list prints it"}),),
    run=reports_show,
    render_text=_render_text,
)
