import re
from html import escape
from urllib.parse import quote

from brigade.dashboard.render_block import Block, render_block
from brigade.dashboard.render_empty_state import render_empty_state
from brigade.dashboard.render_fold import Fold, render_fold
from brigade.dashboard.render_html_table import render_html_table
from brigade.dashboard.render_page_head import PageHead, render_page_head
from brigade.dashboard.render_stat_tile import StatTile, render_stat_tile
from brigade.dashboard.render_status_sentence import render_status_sentence
from brigade.dashboard.render_svg_bar import SvgBar, render_svg_bar

MILESTONE_REPORT = "milestone-report"
TASK_REPORT = "task-report"
WAVE_REPORT = "wave-report"
REPORT_KINDS = (MILESTONE_REPORT, TASK_REPORT, WAVE_REPORT)
HEADER = ("subject", "project", "verdict", "tasks merged", "reported")
MILESTONES_HEADER = (("Milestone", ""), ("Verdict", ""), ("Tasks", ""), ("Runs", "num"), ("Inside", ""))
WAVES_HEADER = (("Wave", ""), ("Verdict", ""), ("Tasks", ""), ("Runs", "num"))
INSIDE = (("REASON", "reason"), ("TESTER_STEP", "tester step"))
NO_PROJECT = "-"
NO_FIGURE = "-"
NO_VERDICT = '<span class="no-verdict">no verdict recorded</span>'
UNDATED = '<span class="no-date">not dated by the ledger</span>'
VERDICT_LABEL = re.compile(r"verdict:\s*", re.IGNORECASE)
MERGED = "merged"
PARKED = "parked"
MERGED_NOTHING = "0"
DATE_LENGTH = len("YYYY-MM-DD")
NO_ROW = ""
HEAD = PageHead(
    title="Reports",
    lede="A report is the written account of a delivery: what was merged, what it cost, what went wrong,"
    " and what to check by hand before you trust it.",
)
EXPLAINER = (
    '<details class="explainer" open><summary>What a report is, and when to read one</summary>'
    "<div><p>When every task of a milestone is merged or parked, brigade writes its report. The <b>CLI fills"
    " the facts</b>: the tasks and their pull requests, the statistics, the SPEC lines to test. A <b>reporting"
    " agent writes the judgment</b>: the verdict, why a task was parked, what went well and wrong, the steps a"
    " tester follows, the code worth reading by sampling.</p>"
    "<p>The report is committed on the branch of the milestone and becomes the body of the pull request you"
    " merge. <b>Read it before that merge</b>, and after any wave you did not watch. If you read three things:"
    " the verdict, what went wrong, the tester steps.</p>"
    "<p>A task that names no milestone gets a task report. Reports named after a wave were written before"
    " milestone reports existed.</p></div></details>"
)
TASK_EMPTY_STATE = (
    "No task of no milestone has been reported.",
    "The tick writes one once the pull request of a task naming no milestone is ready.",
)


def _select(reports: list[dict], kind: str) -> list[dict]:
    return [report for report in reports if report["kind"] == kind]


def _select_newest_first(reports: list[dict], kind: str) -> list[dict]:
    return sorted(_select(reports, kind), key=lambda report: report["reported_at"] or "", reverse=True)


def _count(number: int, noun: str) -> str:
    return f"{number} {noun}" if number == 1 else f"{number} {noun}s"


def _address(report: dict) -> str:
    return escape(f"#reports/{quote(report['id'], safe='')}")


def _name(report: dict) -> str:
    return escape(report["subject"] or report["id"])


def _render_link(report: dict) -> str:
    return f'<a href="{_address(report)}">{_name(report)}</a>'


def _render_verdict(verdict: str | None) -> str:
    if verdict is None:
        return NO_VERDICT
    return escape(VERDICT_LABEL.sub("", verdict, count=1))


def _render_merged(statistics: dict) -> str:
    if "tasks" not in statistics:
        return NO_FIGURE
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


def _render_cell(tag: str, css: str, content: str) -> str:
    opening = f"<{tag}>" if not css else f'<{tag} class="{css}">'
    return f"{opening}{content}</{tag}>"


def _render_classed_table(header: tuple[tuple[str, str], ...], rows: list[tuple[tuple[str, str], ...]]) -> str:
    head = "".join(_render_cell("th", css, escape(name)) for name, css in header)
    body = "".join(f"<tr>{''.join(_render_cell('td', css, content) for css, content in row)}</tr>" for row in rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _render_tasks(statistics: dict) -> tuple[str, str]:
    merged, tasks = int(statistics["merged"]), int(statistics["tasks"])
    label = f"{merged} of {tasks} merged"
    bar = render_svg_bar(SvgBar(label, MERGED if merged == tasks else PARKED, merged, tasks))
    return "", f'{bar}<span class="muted num">{label}</span>'


def _render_inside(counts: dict) -> str:
    return " · ".join(_count(counts[name], noun) for name, noun in INSIDE if counts.get(name))


def _render_title(report: dict) -> str:
    if report["title"] is None:
        return ""
    return f'<br><span class="muted">{escape(report["title"])}</span>'


def _render_milestone_row(report: dict) -> tuple[tuple[str, str], ...]:
    return (
        ("", f'<a href="{_address(report)}"><b class="mono">{_name(report)}</b></a>{_render_title(report)}'),
        ("", _render_verdict(report["verdict"])),
        _render_tasks(report["statistics"]),
        ("num", escape(report["statistics"].get("runs", NO_FIGURE))),
        ("num", _render_inside(report["counts"])),
    )


def _render_milestones(reports: list[dict]) -> str:
    rows = [_render_milestone_row(report) for report in _select_newest_first(reports, MILESTONE_REPORT)]
    table = _render_classed_table(MILESTONES_HEADER, rows)
    return render_block(Block("Milestones", "The newest first.", f'<div class="panel scroll">{table}</div>'))


def _render_wave_row(report: dict) -> tuple[tuple[str, str], ...]:
    return (
        ("", f'<a class="mono" href="{_address(report)}">{_name(report)}</a>'),
        ("", _render_verdict(report["verdict"])),
        _render_tasks(report["statistics"]),
        ("num", escape(report["statistics"].get("runs", NO_FIGURE))),
    )


def _render_waves(reports: list[dict]) -> str:
    waves = _select_newest_first(reports, WAVE_REPORT)
    empty = [report["id"] for report in waves if report["statistics"].get("merged") == MERGED_NOTHING]
    detail = f"{len(waves) - len(empty)} delivered at least one task"
    if empty:
        detail = f"{detail} · {len(empty)} delivered nothing: {', '.join(empty)}"
    table = _render_classed_table(WAVES_HEADER, [_render_wave_row(report) for report in waves])
    fold = render_fold(Fold("Show the wave reports", detail, f'<div class="scroll">{table}</div>'))
    lede = f"{_count(len(waves), 'report')}."
    return render_block(Block("Waves, before milestone reports", lede, f'<div class="panel">{fold}</div>'))


def _render_task_reports(reports: list[dict]) -> str:
    selected = _select(reports, TASK_REPORT)
    if not selected:
        return render_empty_state(*TASK_EMPTY_STATE)
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
            render_page_head(HEAD),
            EXPLAINER,
            _render_sentence(reports),
            _render_tiles(reports),
            _render_milestones(reports),
            _render_section("Task reports", _render_task_reports(reports)),
            _render_waves(reports),
            _render_order_results(reports),
        ]
    )
