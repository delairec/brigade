from html import escape
from urllib.parse import quote

from brigade.dashboard.render_details import render_details
from brigade.dashboard.render_empty_state import render_empty_state
from brigade.dashboard.render_explainer import render_explainer
from brigade.dashboard.render_html_table import render_html_table
from brigade.dashboard.render_stat_tile import StatTile, render_stat_tile
from brigade.dashboard.render_status_sentence import render_status_sentence

MILESTONE_REPORT = "milestone-report"
TASK_REPORT = "task-report"
WAVE_REPORT = "wave-report"
REPORT_KINDS = (MILESTONE_REPORT, TASK_REPORT, WAVE_REPORT)
HEADER = ("subject", "project", "verdict", "tasks merged", "reported")
NO_PROJECT = "-"
NO_TASK_FIGURE = "-"
NO_VERDICT = '<span class="no-verdict">no verdict recorded</span>'
UNDATED = '<span class="no-date">not dated by the ledger</span>'
MERGED_NOTHING = "0"
DATE_LENGTH = len("YYYY-MM-DD")
NO_ROW = ""
EXPLAINER_SUMMARY = (
    "A report is the account brigade writes once a delivery ends: a milestone reached, a task of no milestone"
    " ready to merge, or, before the milestone reports, a wave closed."
)
EXPLAINER_WHAT = (
    "It tells what was delivered and what was not: the tasks merged and parked with their pull requests, the runs,"
    " the lines changed, the manual tests to run, the questions left, and a verdict written on the evidence of the"
    " ledger."
)
EXPLAINER_USE = (
    "Read one before merging the pull request of a milestone or of a task, whose body it is, or to learn why a"
    " delivery went wrong: the verdict of each row says whether it is worth opening."
)
WAVE_FOLD = "the reports of the waves, written before the milestone reports"
EMPTY_STATES = {
    MILESTONE_REPORT: (
        "No milestone has been reported.",
        (
            "The tick writes one once no task of a milestone is left to deliver, and opens with it the pull"
            " request of the milestone into main."
        ),
    ),
    TASK_REPORT: (
        "No task of no milestone has been reported.",
        "The tick writes one once the pull request of a task naming no milestone is ready.",
    ),
    WAVE_REPORT: (
        "No wave report is kept.",
        "None is written any more: only a registry older than the milestone reports holds them.",
    ),
}


def _select(reports: list[dict], kind: str) -> list[dict]:
    return [report for report in reports if report["kind"] == kind]


def _render_link(report: dict) -> str:
    address = f"#reports/{quote(report['id'], safe='')}"
    return f'<a href="{escape(address)}">{escape(report["subject"] or report["id"])}</a>'


def _render_verdict(verdict: str | None) -> str:
    if verdict is None:
        return NO_VERDICT
    return escape(verdict)


def _render_merged(statistics: dict) -> str:
    if "tasks" not in statistics:
        return NO_TASK_FIGURE
    return f"{escape(statistics['merged'])} of {escape(statistics['tasks'])}"


def _render_date(reported_at: str | None) -> str:
    if reported_at is None:
        return UNDATED
    return f'<time datetime="{escape(reported_at)}">{escape(reported_at[:DATE_LENGTH])}</time>'


def _render_table(reports: list[dict]) -> str:
    rows = [
        (
            _render_link(report),
            escape(report["project"] or NO_PROJECT),
            _render_verdict(report["verdict"]),
            _render_merged(report["statistics"]),
            _render_date(report["reported_at"]),
        )
        for report in reports
    ]
    return render_html_table(HEADER, rows, NO_ROW)


def _render_block_body(reports: list[dict], kind: str) -> str:
    selected = _select(reports, kind)
    if not selected:
        return render_empty_state(*EMPTY_STATES[kind])
    return _render_table(selected)


def _render_section(heading: str, body: str) -> str:
    return f"<section><h2>{escape(heading)}</h2>{body}</section>"


def _render_order_results(reports: list[dict]) -> str:
    results = [report for report in reports if report["kind"] not in REPORT_KINDS]
    if not results:
        return NO_ROW
    return _render_section("Order results", _render_table(results))


def _render_sentence(reports: list[dict]) -> str:
    milestones, tasks, waves = (len(_select(reports, kind)) for kind in REPORT_KINDS)
    orders = len(reports) - milestones - tasks - waves
    return render_status_sentence(
        f"{len(reports)} reports: {milestones} on a milestone, {tasks} on a task of no milestone,"
        f" {waves} on a wave, {orders} answering an order."
    )


def _render_tiles(reports: list[dict]) -> str:
    waves = _select(reports, WAVE_REPORT)
    empty_waves = [report for report in waves if report["statistics"].get("merged") == MERGED_NOTHING]
    tiles = (
        StatTile("milestone reports", str(len(_select(reports, MILESTONE_REPORT))), "one per milestone reached"),
        StatTile("task reports", str(len(_select(reports, TASK_REPORT))), "one per task of no milestone"),
        StatTile("wave reports", str(len(waves)), f"{len(empty_waves)} record a wave that merged nothing"),
    )
    return f'<div class="stat-tiles">{"".join(render_stat_tile(tile) for tile in tiles)}</div>'


def render_reports_fragment(document: dict) -> str:
    reports = document["reports"]
    return "".join(
        [
            _render_sentence(reports),
            _render_tiles(reports),
            render_details(EXPLAINER_SUMMARY, render_explainer(EXPLAINER_WHAT, EXPLAINER_USE)),
            _render_section("Milestone reports", _render_block_body(reports, MILESTONE_REPORT)),
            _render_section("Task reports", _render_block_body(reports, TASK_REPORT)),
            _render_section("Wave reports", render_details(WAVE_FOLD, _render_block_body(reports, WAVE_REPORT))),
            _render_order_results(reports),
        ]
    )
