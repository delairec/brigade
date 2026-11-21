import argparse
from collections import Counter

from brigade.command import Command
from brigade.ledger.format_instant import format_instant
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.milestone_reported import MilestoneReported
from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.task_reported import TaskReported
from brigade.ledger.wave_reported import WaveReported
from brigade.registry.read_projects import read_projects
from brigade.reports.read_milestone_title import read_milestone_title
from brigade.reports.read_reports import REPORT_KINDS_BY_FIELD, WAVE_REPORT_KIND, read_reports
from brigade.runtime import Runtime
from brigade.system.render_table import render_table

DOCUMENT_SCHEMA_VERSION = 1
DOCUMENT_KIND = "progress_form"
OPERATIONAL_CORPUS_DOCUMENT = "awawa"
HEADER = ("id", "kind", "project")
NO_PROJECT = "-"
NO_KIND = "-"
NO_REPORT = "no report"
SUBJECT_FIELDS = ("MILESTONE", "TASK", "WAVE")
STATISTIC_FIELD = "STATISTIC"
VERDICT_FIELD = "NARRATIVE"
NO_SUBJECT = None
NO_VERDICT = None
UNDATED = None


def _render_text(document: dict) -> str:
    reports = document["reports"]
    if not reports:
        return NO_REPORT
    return render_table(
        HEADER, [(report["id"], report["kind"] or NO_KIND, report["project"] or NO_PROJECT) for report in reports]
    )


def _identify_milestone_report(event: MilestoneReported) -> tuple[str, str]:
    return (REPORT_KINDS_BY_FIELD["MILESTONE"], f"{event.project}_{event.milestone}")


def _identify_task_report(event: TaskReported) -> tuple[str, str]:
    return (REPORT_KINDS_BY_FIELD["TASK"], f"{event.project}_{event.task}")


def _identify_wave_report(event: WaveReported) -> tuple[str, str]:
    return (WAVE_REPORT_KIND, event.wave)


REPORT_IDENTIFIERS_BY_EVENT = {
    MilestoneReported: _identify_milestone_report,
    TaskReported: _identify_task_report,
    WaveReported: _identify_wave_report,
}


def _read_reported_instants(entries: tuple[LedgerEntry, ...]) -> dict[tuple[str, str], str]:
    return {
        REPORT_IDENTIFIERS_BY_EVENT[type(entry.event)](entry.event): format_instant(entry.instant)
        for entry in entries
        if type(entry.event) in REPORT_IDENTIFIERS_BY_EVENT
    }


def _read_values(report: dict, names: tuple[str, ...]) -> list[str]:
    return [field["value"] for field in report["fields"] if field["name"] in names]


def _describe(report: dict, reported_instants: dict[tuple[str, str], str], title: str | None) -> dict:
    statistics = [value.partition(" ") for value in _read_values(report, (STATISTIC_FIELD,))]
    return {
        **{column: report[column] for column in HEADER},
        "subject": next(iter(_read_values(report, SUBJECT_FIELDS)), NO_SUBJECT),
        "statistics": {name: value for name, _, value in statistics},
        "verdict": next(iter(_read_values(report, (VERDICT_FIELD,))), NO_VERDICT),
        "counts": dict(Counter(field["name"] for field in report["fields"])),
        "reported_at": reported_instants.get((report["kind"], report["id"]), UNDATED),
        "title": title,
    }


def report_list(request: argparse.Namespace, runtime: Runtime) -> dict:
    reported_instants = _read_reported_instants(read_ledger(runtime.paths.state_root).entries)
    projects = read_projects(runtime)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "reports": [
            _describe(report, reported_instants, read_milestone_title(runtime.run_process, projects, report))
            for report in read_reports(runtime, runtime.resolve_plugin(DOCUMENT_KIND, OPERATIONAL_CORPUS_DOCUMENT))
        ],
    }


COMMAND = Command(
    path=("report", "list"),
    help="print one row per wave, task and milestone report and per order result",
    run=report_list,
    render_text=_render_text,
)
