import re
from dataclasses import dataclass
from html import escape
from urllib.parse import quote

from brigade.dashboard.render_block import Block, render_block
from brigade.dashboard.render_fold import Fold, render_fold
from brigade.dashboard.render_key_values import render_key_values
from brigade.dashboard.render_page_head import Crumb, PageHead, render_page_head
from brigade.dashboard.render_stat_tile import StatTile, render_stat_tile
from brigade.dashboard.render_status_pill import render_status_pill
from brigade.dashboard.render_steps import render_steps
from brigade.ledger.count_runs import count_runs

NARRATIVE = "NARRATIVE"
VERDICT = "verdict"
WENT_WRONG = "Went wrong"
WENT_WELL = "Went well"
NEXT_WAVE = "For the next wave"
TASK_ROW = "TASK_ROW"
GRAPH = "GRAPH"
TESTER_STEP = "TESTER_STEP"
MANUAL_TEST = "MANUAL_TEST"
HELD = ("REASON", "PARKED_QUESTION")
SAMPLING = "SAMPLING"
STATISTIC = "STATISTIC"
MILESTONE = "MILESTONE"
SHOWN_FIELDS = (NARRATIVE, TASK_ROW, GRAPH, TESTER_STEP, MANUAL_TEST, *HELD, SAMPLING, STATISTIC, MILESTONE, "PROJECT")
STATISTIC_FILES = "files "
MERGED = "merged"
PARKED = "parked"
RUN_FINISHED = "run.finished"
NOT_RECORDED = "not recorded"
NO_FIGURE = "-"
FLAGGED_ROUNDS = 3
DATE_LENGTH = len("YYYY-MM-DD")
EVERY_TASK = "Every task"
PANEL_LINES = "panel lines"
FOLDED_LINES = "lines"
TASK_NAME = re.compile(r"\b[A-Z][A-Z0-9]*\d+\b")
LINKED_TOKEN = re.compile(
    r"#(?P<pull_request>\d+)\b|(?P<run>\b\d{8}T\d{6}Z-[0-9a-f]+\b)|(?P<task>\b[A-Z][A-Z0-9]*\d+\b)"
)
TASKS_HEADER = (
    ("Task", ""),
    ("State", ""),
    ("Pull requests", ""),
    ("Comes after", ""),
    ("Review rounds", "num"),
    ("Cost", "num"),
)
MS_PER_MINUTE = 60000
MINUTES_PER_HOUR = 60


@dataclass(frozen=True)
class ReportReading:
    document: dict
    waves: list[dict]
    pull_request_address: str | None


@dataclass(frozen=True)
class _Linker:
    wave_of_task: dict[str, str]
    pull_request_address: str | None

    def link(self, value: str) -> str:
        pieces = []
        written = 0
        for token in LINKED_TOKEN.finditer(value):
            address = self._address(token)
            if address is None:
                continue
            pieces.append(escape(value[written : token.start()]))
            pieces.append(f'<a href="{escape(address)}">{escape(token.group())}</a>')
            written = token.end()
        pieces.append(escape(value[written:]))
        return "".join(pieces)

    def link_task(self, task: str) -> str:
        address = self._address_task(task)
        if address is None:
            return escape(task)
        return f'<a class="mono" href="{escape(address)}">{escape(task)}</a>'

    def _address_task(self, task: str) -> str | None:
        wave = self.wave_of_task.get(task)
        return None if wave is None else f"#waves/{quote(wave, safe='')}"

    def _address(self, token: re.Match) -> str | None:
        if token.group("pull_request") is not None:
            if self.pull_request_address is None:
                return None
            return f"{self.pull_request_address}{token.group('pull_request')}"
        if token.group("run") is not None:
            return f"#runs/{quote(token.group('run'), safe='')}"
        return self._address_task(token.group("task"))


def _read_values(fields: list[dict], names: tuple[str, ...]) -> list[str]:
    return [field["value"] for field in fields if field["name"] in names]


def _count(number: int, noun: str) -> str:
    return f"{number} {noun}" if number == 1 else f"{number} {noun}s"


def _format_duration(milliseconds: int) -> str:
    hours, minutes = divmod(milliseconds // MS_PER_MINUTE, MINUTES_PER_HOUR)
    return f"{minutes} min" if hours == 0 else f"{hours} h {minutes} min"


def _render_files_tile(fields: list[dict], merged: int) -> str:
    files = next(
        (
            value.removeprefix(STATISTIC_FILES)
            for value in _read_values(fields, (STATISTIC,))
            if value.startswith(STATISTIC_FILES)
        ),
        None,
    )
    if files is None:
        return ""
    tile = render_stat_tile(StatTile("files changed", files, "the statistic of the report"))
    if files != "0" or merged == 0:
        return tile
    questioned = StatTile("files changed", files, f"questioned: the ledger records {merged} tasks merged")
    return render_stat_tile(questioned).replace('class="stat-tile"', 'class="stat-tile questioned"', 1)


def _render_tiles(waves: list[dict], fields: list[dict]) -> str:
    if not waves:
        return ""
    perimeter = f"the waves {', '.join(wave['wave'] for wave in waves)}"
    tasks = [task for wave in waves for task in wave["tasks"]]
    merged = sum(task["state"] == MERGED for task in tasks)
    turns = sum(sum(wave["ledger"]["turns_by_task"].values()) for wave in waves)
    costs = [wave["ledger"]["cost_usd"] for wave in waves if wave["ledger"]["cost_usd"] is not None]
    run_times = [
        task["duration_ms"] for wave in waves for task in wave["ledger"]["by_task"] if task["duration_ms"] is not None
    ]
    count = count_runs(
        event["fields"] for wave in waves for event in wave["ledger"]["events"] if event["event"] == RUN_FINISHED
    )
    wall_time = sum(wave["ledger"]["wall_time_ms"] for wave in waves)
    cost_perimeter = perimeter if count.costless == 0 else f"a floor: {count.costless} runs record no cost"
    run_time = f"{_format_duration(sum(run_times))} of run time" if run_times else f"run time {NOT_RECORDED}"
    tiles = [
        StatTile("tasks merged", f"{merged} of {len(tasks)}", perimeter),
        StatTile("runs", f"{count.runs} runs, {turns} turns", perimeter),
        StatTile("cost", f"{sum(costs):.2f} USD" if costs else NOT_RECORDED, cost_perimeter),
        StatTile("wall time", _format_duration(wall_time), run_time),
    ]
    rendered = "".join(render_stat_tile(tile) for tile in tiles)
    return f'<div class="tiles">{rendered}{_render_files_tile(fields, merged)}</div>'


def _recognise_label(words: str) -> str | None:
    if words == VERDICT:
        return VERDICT
    if "went wrong" in words:
        return WENT_WRONG
    if "went well" in words:
        return WENT_WELL
    if words.startswith("next"):
        return NEXT_WAVE
    return None


def _read_label(value: str) -> tuple[str | None, str]:
    label, colon, rest = value.partition(":")
    if not colon:
        return None, value
    group = _recognise_label(label.strip().lower())
    return (None, value) if group is None else (group, rest.strip())


def _sort_narrative(fields: list[dict]) -> dict[str | None, list[str]]:
    sorted_narrative: dict[str | None, list[str]] = {}
    for value in _read_values(fields, (NARRATIVE,)):
        group, line = _read_label(value)
        sorted_narrative.setdefault(group, []).append(line)
    return sorted_narrative


def _render_lines(values: list[str], linker: _Linker, css: str) -> str:
    return f'<ul class="{css}">{"".join(f"<li><p>{linker.link(value)}</p></li>" for value in values)}</ul>'


def _render_pull_request(document: dict, address: str | None) -> str:
    label = f"pull request #{document['pull_request']}"
    if address is None:
        return label
    return f'<a href="{escape(address)}{document["pull_request"]}">{label}</a>'


def _render_fresh(document: dict, address: str | None) -> str:
    parts = []
    if document["pull_request"] is not None:
        parts.append(f"body of {_render_pull_request(document, address)}")
    if document["reported_at"] is not None:
        parts.append(escape(f"reported {document['reported_at'][:DATE_LENGTH]}"))
    return f'<p class="fresh">{", ".join(parts)}</p>'


def _render_merged_pill(rows: list[tuple[str, str, list[str]]]) -> str:
    merged = sum(row[1] == MERGED for row in rows)
    state = MERGED if merged == len(rows) else PARKED
    return render_status_pill(state, f"{merged} of {len(rows)} merged")


def _render_head(reading: ReportReading, lede: str, rows: list[tuple[str, str, list[str]]]) -> str:
    report = reading.document["report"]
    labels = (report["project"], report["kind"].replace("-", " "))
    crumbs = (Crumb("Reports", "#reports"), *(Crumb(label, "") for label in labels if label is not None))
    fresh = _render_fresh(reading.document, reading.pull_request_address)
    milestones = _read_values(report["fields"], (MILESTONE,))
    if not milestones:
        return render_page_head(PageHead(title="Report", lede=lede, name=report["id"], crumbs=crumbs, fresh=fresh))
    pill = _render_merged_pill(rows)
    head = PageHead(
        title="Milestone",
        lede=lede,
        name=milestones[0],
        crumbs=crumbs,
        fresh=fresh,
        pill=pill,
        caption=reading.document["title"] or "",
    )
    return render_page_head(head)


def _render_narrative_block(heading: str, lines: list[str], linker: _Linker) -> str:
    return render_block(Block(heading, _count(len(lines), "line"), _render_lines(lines, linker, PANEL_LINES)))


def _render_split(narrative: dict[str | None, list[str]], linker: _Linker) -> str:
    if not any(heading in narrative for heading in (WENT_WRONG, WENT_WELL, NEXT_WAVE)):
        return ""
    wrong, well, following = (
        _render_narrative_block(heading, narrative.get(heading, []), linker)
        for heading in (WENT_WRONG, WENT_WELL, NEXT_WAVE)
    )
    return f'<div class="split">{wrong}<div class="block">{well}{following}</div></div>'


def _render_cell(tag: str, css: str, content: str) -> str:
    opening = f"<{tag}>" if not css else f'<{tag} class="{css}">'
    return f"{opening}{content}</{tag}>"


def _render_table(header: tuple[tuple[str, str], ...], rows: list[tuple[tuple[str, str], ...]]) -> str:
    head = "".join(_render_cell("th", css, escape(name)) for name, css in header)
    body = "".join(f"<tr>{''.join(_render_cell('td', css, content) for css, content in row)}</tr>" for row in rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _read_task_row(value: str) -> tuple[str, str, list[str]]:
    task, _, rest = value.partition(" ")
    state, _, numbers = rest.partition(" ")
    return task, state, numbers.split()


def _render_pull_requests(numbers: list[str], linker: _Linker) -> str:
    if len(numbers) < 2:
        return "".join(linker.link(number) for number in numbers)
    return f'{linker.link(numbers[0])} <span class="muted">· {escape(" · ".join(numbers[1:]))}</span>'


def _read_rounds(task: str, state: str, waves: list[dict]) -> int | None:
    ledgers = [wave["ledger"] for wave in waves]
    merged_rounds = [
        pull_request["rounds"]
        for ledger in ledgers
        for pull_request in ledger["pull_requests"]
        if state == MERGED and pull_request["task"] == task
    ]
    held_rounds = [ledger["rounds_by_task"][task] for ledger in ledgers if task in ledger["rounds_by_task"]]
    return next(iter([*merged_rounds, *held_rounds]), None)


def _render_rounds(rounds: int | None) -> tuple[str, str]:
    if rounds is None:
        return "num", NO_FIGURE
    return ("num flag" if rounds >= FLAGGED_ROUNDS else "num"), str(rounds)


def _render_cost(task: str, waves: list[dict]) -> tuple[str, str]:
    costs = [
        cost["cost_usd"]
        for wave in waves
        for cost in wave["ledger"]["by_task"]
        if cost["task"] == task and cost["cost_usd"] is not None
    ]
    return "num", f"{sum(costs):.2f}" if costs else NO_FIGURE


def _render_after(after: list[str]) -> tuple[str, str]:
    if not after:
        return "muted", NO_FIGURE
    return "mono", escape(", ".join(after))


def _render_task_row(
    row: tuple[str, str, list[str]], afters: dict[str, list[str]], reading: ReportReading, linker: _Linker
) -> tuple:
    task, state, numbers = row
    return (
        ("", linker.link_task(task)),
        ("", render_status_pill(state)),
        ("", _render_pull_requests(numbers, linker)),
        _render_after(afters.get(task, [])),
        _render_rounds(_read_rounds(task, state, reading.waves)),
        _render_cost(task, reading.waves),
    )


def _render_tasks(reading: ReportReading, rows: list[tuple[str, str, list[str]]], linker: _Linker) -> str:
    if not rows:
        return ""
    afters: dict[str, list[str]] = {}
    for value in _read_values(reading.document["report"]["fields"], (GRAPH,)):
        task, _, after = value.partition(" after ")
        afters.setdefault(task, []).append(after)
    table = _render_table(TASKS_HEADER, [_render_task_row(row, afters, reading, linker) for row in rows])
    waves = ", ".join(wave["wave"] for wave in reading.waves)
    cap = f'<p class="cap">Rounds and cost come from the ledger of the waves {escape(waves)}.</p>'
    lede = "What the milestone delivered, and in what order."
    return render_block(Block("Tasks", lede, f'<div class="panel scroll">{table}{cap}</div>'))


def _group_steps(values: list[str]) -> dict[str | None, list[str]]:
    groups: dict[str | None, list[str]] = {}
    for value in values:
        leading = TASK_NAME.match(value)
        if leading is None:
            groups.setdefault(None, []).append(value)
            continue
        groups.setdefault(leading.group(), []).append(value[leading.end() :].lstrip(": "))
    return groups


def _render_steps_by_task(fields: list[dict], linker: _Linker) -> str:
    values = _read_values(fields, (TESTER_STEP,))
    if not values:
        return ""
    groups = sorted(_group_steps(values).items(), key=lambda group: group[0] is None)
    folds = "".join(
        render_fold(
            Fold(
                summary=EVERY_TASK if task is None else task,
                detail=_count(len(steps), "step"),
                body=render_steps(tuple(linker.link(step) for step in steps)),
            )
        )
        for task, steps in groups
    )
    lede = f"{_count(len(values), 'step')} in a tester's words, by task. Do these before you trust the merge."
    return render_block(Block("Test it by hand", lede, f'<div class="panel">{folds}</div>'))


def _render_held(fields: list[dict], linker: _Linker) -> str:
    reasons = _read_values(fields, HELD)
    lede = f"{_count(len(reasons), 'reason')}."
    return render_block(Block("Why a task was held", lede, _render_lines(reasons, linker, PANEL_LINES)))


def _render_sampled(value: str, linker: _Linker) -> str:
    named = TASK_NAME.search(value)
    tag = "" if named is None else f'<span class="tag">{escape(named.group())}</span>'
    return f"<li><p>{tag}{linker.link(value)}</p></li>"


def _render_sampling(fields: list[dict], linker: _Linker) -> str:
    places = _read_values(fields, (SAMPLING,))
    lede = f"{_count(len(places), 'place')} the reporter picked for a review by sampling."
    body = f'<ul class="{PANEL_LINES}">{"".join(_render_sampled(place, linker) for place in places)}</ul>'
    return render_block(Block("Worth reading in the code", lede, body))


def _render_account(fields: list[dict], happened: list[str], linker: _Linker) -> str:
    specs = _read_values(fields, (MANUAL_TEST,))
    others = [(field["name"], linker.link(field["value"])) for field in fields if field["name"] not in SHOWN_FIELDS]
    folds = (
        Fold("What happened", _count(len(happened), "narrative line"), _render_lines(happened, linker, FOLDED_LINES)),
        Fold("The SPEC lines to test", _count(len(specs), "line"), _render_lines(specs, linker, FOLDED_LINES)),
        Fold("Statistics as the CLI filled them", " · ".join(_read_values(fields, (STATISTIC,))), ""),
        Fold("Other fields", " · ".join(dict.fromkeys(name for name, _ in others)), render_key_values(tuple(others))),
    )
    body = f'<div class="panel">{"".join(render_fold(fold) for fold in folds)}</div>'
    return render_block(Block("The full account", "Everything else the report holds, as written.", body))


def render_report_fragment(reading: ReportReading) -> str:
    fields = reading.document["report"]["fields"]
    linker = _Linker(
        {task["task"]: wave["wave"] for wave in reading.waves for task in wave["tasks"]}, reading.pull_request_address
    )
    narrative = _sort_narrative(fields)
    candidates = [*narrative.get(VERDICT, []), *narrative.get(None, [])]
    rows = [_read_task_row(value) for value in _read_values(fields, (TASK_ROW,))]
    return (
        _render_head(reading, next(iter(candidates), ""), rows)
        + _render_tiles(reading.waves, fields)
        + _render_split(narrative, linker)
        + _render_tasks(reading, rows, linker)
        + _render_steps_by_task(fields, linker)
        + _render_held(fields, linker)
        + _render_sampling(fields, linker)
        + _render_account(fields, candidates[1:], linker)
    )
