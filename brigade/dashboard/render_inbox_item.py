from html import escape

from brigade.dashboard.render_block import Block, render_block
from brigade.dashboard.render_fragment import render_fragment
from brigade.dashboard.render_html_table import render_html_table
from brigade.dashboard.render_key_values import render_key_values
from brigade.dashboard.render_page_head import Crumb, PageHead, render_page_head
from brigade.reports.manual_test_tables import MANUAL_TEST_HEADER, MANUAL_TEST_TABLES

ANSWER_KEY = "answer"
PATTERN_KEY = "pattern"
STUDY_ANSWER_KIND = "study-answer"
NOT_NAMED = "-"
INBOX_ADDRESS = "#inbox"
PATTERN_LEDE = "Proposed by the triage: ratify or dismiss it from the inbox."


def _render_pattern(pattern: dict) -> str:
    name = pattern["name"]
    head = PageHead(
        title=pattern["title"],
        lede=PATTERN_LEDE,
        crumbs=(Crumb("Inbox", INBOX_ADDRESS), Crumb(name, "")),
    )
    facts = (
        ("Pattern", f"<code>{escape(name)}</code>"),
        ("Action", escape(pattern["action"] or NOT_NAMED)),
        ("Target", escape(pattern["target"] or NOT_NAMED)),
    )
    evidence = "".join(f"<li>{escape(line)}</li>" for line in pattern["evidence"])
    return (
        f"{render_page_head(head)}{render_key_values(facts)}"
        f"{render_block(Block(title='Evidence', lede='', body=f'<ul>{evidence}</ul>'))}"
    )


def _render_table(heading: str, values: list[str]) -> str:
    rows = [(str(rank), escape(value)) for rank, value in enumerate(values, start=1)]
    return f"<h3>{escape(heading)}</h3>{render_html_table(MANUAL_TEST_HEADER, rows, heading)}"


def render_inbox_item(document: dict) -> str:
    if PATTERN_KEY in document:
        return _render_pattern(document[PATTERN_KEY])
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
