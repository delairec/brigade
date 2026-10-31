from html import escape
from urllib.parse import quote

from brigade.dashboard.render_html_table import render_html_table

HEADER = ("run", "procedure", "project", "wave", "task", "state", "outcome")
ABSENT = "-"
NO_RUN = "no run"


def _render_link(run_id: str) -> str:
    address = f"#runs/{quote(run_id, safe='')}"
    return f'<a href="{escape(address)}">{escape(run_id)}</a>'


def _show(value: str | None) -> str:
    return ABSENT if value is None else escape(value)


def render_runs_fragment(document: dict) -> str:
    rows = [
        (_render_link(listed["run"]), *(_show(listed[column]) for column in HEADER[1:])) for listed in document["runs"]
    ]
    return render_html_table(HEADER, rows, NO_RUN)
