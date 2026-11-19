from html import escape

from brigade.dashboard.render_fragment import render_fragment
from brigade.dashboard.render_html_table import render_html_table
from brigade.reports.manual_test_tables import MANUAL_TEST_HEADER, MANUAL_TEST_TABLES

ANSWER_KEY = "answer"
STUDY_ANSWER_KIND = "study-answer"


def _render_table(heading: str, values: list[str]) -> str:
    rows = [(str(rank), escape(value)) for rank, value in enumerate(values, start=1)]
    return f"<h3>{escape(heading)}</h3>{render_html_table(MANUAL_TEST_HEADER, rows, heading)}"


def render_inbox_item(document: dict) -> str:
    if ANSWER_KEY not in document:
        return render_fragment(document)
    answer = document[ANSWER_KEY]
    fields = answer["fields"]
    listed = "".join(
        f"<dt>{escape(field['name'])}</dt><dd>{escape(field['value'])}</dd>"
        for field in fields
        if field["name"] not in MANUAL_TEST_TABLES
    )
    tables = "".join(
        _render_table(heading, values)
        for name, heading in MANUAL_TEST_TABLES.items()
        if (values := [field["value"] for field in fields if field["name"] == name])
    )
    return f"<h2>{escape(STUDY_ANSWER_KIND)} {escape(answer['id'])}</h2><dl>{listed}</dl>{tables}"
