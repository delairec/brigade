import re
from dataclasses import dataclass
from html import escape
from urllib.parse import quote

from brigade.dashboard.render_details import render_details
from brigade.dashboard.render_html_table import render_html_table
from brigade.dashboard.render_stat_tile import StatTile, render_stat_tile

NARRATIVE = "NARRATIVE"
VERDICT = "verdict"
NARRATIVE_BLOCKS = {"went wrong": "Went wrong", "went well": "Went well", "next": "For the next wave"}
TASK_TABLES = {"TASK_ROW": ("task",), "GRAPH": ("dependency",)}
BY_HAND = ("TESTER_STEP", "MANUAL_TEST")
HELD = ("REASON", "PARKED_QUESTION")
SAMPLING = "SAMPLING"
STATISTIC_FILES = "files "
MERGED = "merged"
LEADING_TASK = re.compile(r"[A-Z][A-Z0-9]*\d+\b")
LINKED_TOKEN = re.compile(
    r"#(?P<pull_request>\d+)\b|(?P<run>\b\d{8}T\d{6}Z-[0-9a-f]+\b)|(?P<task>\b[A-Z][A-Z0-9]*\d+\b)"
)
SHOWN_FIELDS = (NARRATIVE, *TASK_TABLES, *BY_HAND, *HELD, SAMPLING)
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

    def _address(self, token: re.Match) -> str | None:
        if token.group("pull_request") is not None:
            if self.pull_request_address is None:
                return None
            return f"{self.pull_request_address}{token.group('pull_request')}"
        if token.group("run") is not None:
            return f"#runs/{quote(token.group('run'), safe='')}"
        wave = self.wave_of_task.get(token.group("task"))
        return None if wave is None else f"#waves/{quote(wave, safe='')}"


def _read_values(fields: list[dict], names: tuple[str, ...]) -> list[str]:
    return [field["value"] for field in fields if field["name"] in names]


def _read_leading(value: str) -> str | None:
    lowered = value.lower()
    return next((words for words in (VERDICT, *NARRATIVE_BLOCKS) if lowered.startswith(words)), None)


def _render_list(values: list[str], linker: _Linker, tag: str = "ul") -> str:
    if not values:
        return ""
    return f"<{tag}>{''.join(f'<li>{linker.link(value)}</li>' for value in values)}</{tag}>"


def _render_block(heading: str, content: str) -> str:
    return "" if not content else f"<h3>{escape(heading)}</h3>{content}"


def _format_duration(milliseconds: int) -> str:
    hours, minutes = divmod(milliseconds // MS_PER_MINUTE, MINUTES_PER_HOUR)
    return f"{minutes} min" if hours == 0 else f"{hours} h {minutes} min"


def _render_files_tile(fields: list[dict], merged: int) -> str:
    files = next(
        (
            value.removeprefix(STATISTIC_FILES)
            for value in _read_values(fields, ("STATISTIC",))
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
    runs = [slot["runs"] for wave in waves for slot in wave["ledger"]["turns"]["by_slot"].values()]
    unmeasured = sum(count["unmeasured"] for count in runs)
    turns = sum(sum(wave["ledger"]["turns_by_task"].values()) for wave in waves)
    cost = sum(wave["ledger"]["cost_usd"] for wave in waves)
    run_time = sum(task["duration_ms"] for wave in waves for task in wave["ledger"]["by_task"])
    wall_time = sum(wave["ledger"]["wall_time_ms"] for wave in waves)
    cost_perimeter = perimeter if unmeasured == 0 else f"a floor: {unmeasured} runs record no cost"
    tiles = [
        StatTile("tasks merged", f"{merged} of {len(tasks)}", perimeter),
        StatTile("runs", f"{sum(count['measured'] for count in runs) + unmeasured} runs, {turns} turns", perimeter),
        StatTile("cost", f"{cost:.2f} USD", cost_perimeter),
        StatTile("wall time", _format_duration(wall_time), f"{_format_duration(run_time)} of run time"),
    ]
    rendered = "".join(render_stat_tile(tile) for tile in tiles)
    return f'<div class="tiles">{rendered}{_render_files_tile(fields, merged)}</div>'


def _group_by_task(values: list[tuple[str, str]]) -> dict[str | None, list[tuple[str, str]]]:
    groups: dict[str | None, list[tuple[str, str]]] = {}
    for name, value in values:
        leading = LEADING_TASK.match(value)
        groups.setdefault(None if leading is None else leading.group(), []).append((name, value))
    return groups


def _render_groups(fields: list[dict], names: tuple[str, ...], linker: _Linker) -> str:
    values = [(field["name"], field["value"]) for field in fields if field["name"] in names]
    rendered = []
    for task, grouped in _group_by_task(values).items():
        heading = "" if task is None else f"<h4>{linker.link(task)}</h4>"
        lists = "".join(
            _render_list(
                [value for field, value in grouped if field == name],
                linker,
                "ol" if rank == 0 and len(names) > 1 else "ul",
            )
            for rank, name in enumerate(names)
        )
        rendered.append(f"{heading}{lists}")
    return "".join(rendered)


def _render_tables(fields: list[dict], linker: _Linker) -> str:
    return "".join(
        render_html_table(header, [(linker.link(value),) for value in values], header[0])
        for name, header in TASK_TABLES.items()
        if (values := _read_values(fields, (name,)))
    )


def _render_delivery(document: dict, linker: _Linker) -> str:
    parts = []
    if document["reported_at"] is not None:
        parts.append(escape(f"reported {document['reported_at']}"))
    if document["pull_request"] is not None:
        number = document["pull_request"]
        parts.append(f"pull request {linker.link(f'#{number}')}")
    return "" if not parts else f'<p class="report-delivery">{", ".join(parts)}</p>'


def _sort_narrative(fields: list[dict]) -> dict[str | None, list[str]]:
    sorted_narrative: dict[str | None, list[str]] = {}
    for value in _read_values(fields, (NARRATIVE,)):
        sorted_narrative.setdefault(_read_leading(value), []).append(value)
    return sorted_narrative


def _render_verdict(reading: ReportReading, verdict: list[str], linker: _Linker) -> str:
    report = reading.document["report"]
    sentences = "".join(f'<p class="status-sentence">{linker.link(value)}</p>' for value in verdict)
    heading = f"<h2>{escape(report['kind'])} {escape(report['id'])}</h2>"
    delivery = _render_delivery(reading.document, linker)
    return f'<section class="report-verdict">{heading}{sentences}{delivery}</section>'


def _render_folded(fields: list[dict], linker: _Linker) -> str:
    folded = "".join(
        f"<dt>{escape(field['name'])}</dt><dd>{linker.link(field['value'])}</dd>"
        for field in fields
        if field["name"] not in SHOWN_FIELDS
    )
    return "" if not folded else render_details("The full account", f"<dl>{folded}</dl>")


def render_report_fragment(reading: ReportReading) -> str:
    fields = reading.document["report"]["fields"]
    linker = _Linker(
        {task["task"]: wave["wave"] for wave in reading.waves for task in wave["tasks"]}, reading.pull_request_address
    )
    narrative = _sort_narrative(fields)
    blocks = "".join(
        _render_block(heading, _render_list(narrative.get(words, []), linker))
        for words, heading in NARRATIVE_BLOCKS.items()
    )
    return (
        _render_verdict(reading, narrative.get(VERDICT, []), linker)
        + _render_tiles(reading.waves, fields)
        + blocks
        + _render_list(narrative.get(None, []), linker)
        + _render_block("Tasks", _render_tables(fields, linker))
        + _render_block("Test it by hand", _render_groups(fields, BY_HAND, linker))
        + _render_block("Why a task was held", _render_list(_read_values(fields, HELD), linker))
        + _render_block("Worth reading in the code", _render_groups(fields, (SAMPLING,), linker))
        + _render_folded(fields, linker)
    )
