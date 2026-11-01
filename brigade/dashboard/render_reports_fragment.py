from html import escape
from urllib.parse import quote

from brigade.dashboard.render_html_table import render_html_table

HEADER = ("id", "kind", "project")
NO_PROJECT = "-"
NO_REPORT = "no report"


def _render_link(report_id: str) -> str:
    address = f"#reports/{quote(report_id, safe='')}"
    return f'<a href="{escape(address)}">{escape(report_id)}</a>'


def render_reports_fragment(document: dict) -> str:
    rows = [
        (_render_link(report["id"]), escape(report["kind"]), escape(report["project"] or NO_PROJECT))
        for report in document["reports"]
    ]
    return render_html_table(HEADER, rows, NO_REPORT)
