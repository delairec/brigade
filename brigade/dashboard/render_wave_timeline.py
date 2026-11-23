from datetime import datetime, timedelta
from html import escape

from brigade.dashboard.format_clock import format_clock
from brigade.dashboard.format_span import format_span
from brigade.dashboard.read_state_tone import read_state_tone
from brigade.dashboard.render_legend import LegendItem, render_legend

CHART_WIDTH = 800
LABEL_WIDTH = 60
TRACK_END = 783
TOP = 8
ROW_HEIGHT = 28
BAR_OFFSET = 12
BAR_HEIGHT = 16
LABEL_OFFSET = 23
AXIS_OFFSET = 16
BOTTOM_MARGIN = 6
HALT_OPACITY = "0.35"
WAITING_OPACITY = ' fill-opacity="0.45"'
WORKING_OPACITY = ""
WAITING_STATES = ("pr_open", "fixing", "rebasing", "changes_requested")
MERGED = "merged"
TICK_WIDTH = "1"
MILLISECONDS_PER_SECOND = 1000
SHORTEST_WAVE_MS = 1
TASK_STATE_EVENT = "task.state"
HOUR = timedelta(hours=1)
HOUR_FORMAT = "%H:00"
CLEARANCE_FROM_END_LABELS = 90
LEGEND = (
    LegendItem(label="building", state="running"),
    LegendItem(label="fixing or rebasing", state="fixing", soft=True),
    LegendItem(label="pull request open, waiting", state="pr_open", soft=True),
    LegendItem(label="verifying", state="verifying"),
    LegendItem(label="merged", state="merged"),
    LegendItem(label="wave halted", state="parked", soft=True),
)


def _measure_ms(start: str, end: str) -> int:
    elapsed = datetime.fromisoformat(end) - datetime.fromisoformat(start)
    return round(elapsed.total_seconds() * MILLISECONDS_PER_SECOND)


def _place(at: str, ledger: dict) -> str:
    span = max(ledger["wall_time_ms"], SHORTEST_WAVE_MS)
    x = LABEL_WIDTH + _measure_ms(ledger["first"], at) / span * (TRACK_END - LABEL_WIDTH)
    return f"{round(x, 1):g}"


def _render_span(start: str, end: str, ledger: dict) -> str:
    width = float(_place(end, ledger)) - float(_place(start, ledger))
    return f'x="{_place(start, ledger)}" width="{round(width, 1):g}"'


def _render_halt(halt: dict, ledger: dict, height: int) -> str:
    end = halt["resumed_at"] or ledger["last"]
    return (
        f'<rect class="tone-{read_state_tone("parked")}" {_render_span(halt["halted_at"], end, ledger)} y="{TOP}"'
        f' height="{height}" fill-opacity="{HALT_OPACITY}"><title>wave halted from'
        f" {format_clock(halt['halted_at'])} to {format_clock(end)}</title></rect>"
    )


def _render_tick(event: dict, ledger: dict, y: int) -> str:
    fields = event["fields"]
    title = f"{fields['task']} {fields['state']} at {format_clock(event['at'])}"
    return (
        f'<rect class="tone-{read_state_tone(fields["state"])}" x="{_place(event["at"], ledger)}" width="{TICK_WIDTH}"'
        f' y="{y}" height="{BAR_HEIGHT}"><title>{escape(title)}</title></rect>'
    )


def _render_bar(event: dict, end: str, ledger: dict, y: int) -> str:
    fields = event["fields"]
    if fields["state"] == MERGED:
        return _render_tick(event, ledger, y)
    opacity = WAITING_OPACITY if fields["state"] in WAITING_STATES else WORKING_OPACITY
    title = (
        f"{fields['task']} {fields['state']} from {format_clock(event['at'])} to {format_clock(end)},"
        f" {format_span(_measure_ms(event['at'], end))}"
    )
    return (
        f'<rect class="tone-{read_state_tone(fields["state"])}" {_render_span(event["at"], end, ledger)} y="{y}"'
        f' height="{BAR_HEIGHT}"{opacity}><title>{escape(title)}</title></rect>'
    )


def _render_row(task: str, index: int, ledger: dict) -> str:
    top = TOP + ROW_HEIGHT * index
    states = [
        event for event in ledger["events"] if event["event"] == TASK_STATE_EVENT and event["fields"]["task"] == task
    ]
    ends = [event["at"] for event in states[1:]] + [ledger["last"]]
    bars = "".join(_render_bar(event, end, ledger, top + BAR_OFFSET) for event, end in zip(states, ends, strict=False))
    return f'<text class="g-label" x="0" y="{top + LABEL_OFFSET}">{escape(task)}</text>{bars}'


def _list_hours(ledger: dict) -> list[datetime]:
    last = datetime.fromisoformat(ledger["last"])
    hour = datetime.fromisoformat(ledger["first"]).replace(minute=0, second=0, microsecond=0) + HOUR
    hours = []
    while hour < last:
        hours.append(hour)
        hour += HOUR
    return hours


def _render_grid_line(hour: datetime, ledger: dict, bottom: int) -> str:
    x = _place(hour.isoformat(), ledger)
    return f'<line class="g-grid" x1="{x}" y1="{TOP}" x2="{x}" y2="{bottom}"></line>'


def _is_clear_of_end_labels(hour: datetime, ledger: dict) -> bool:
    x = float(_place(hour.isoformat(), ledger))
    return LABEL_WIDTH + CLEARANCE_FROM_END_LABELS <= x <= TRACK_END - CLEARANCE_FROM_END_LABELS


def _render_hour_label(hour: datetime, ledger: dict, axis: int) -> str:
    x = _place(hour.isoformat(), ledger)
    return f'<text class="g-text" x="{x}" y="{axis}" text-anchor="middle">{hour.strftime(HOUR_FORMAT)}</text>'


def render_wave_timeline(ledger: dict) -> str:
    rows_height = ROW_HEIGHT * len(ledger["tasks"])
    axis = TOP + rows_height + AXIS_OFFSET
    hours = _list_hours(ledger)
    grid = "".join(_render_grid_line(hour, ledger, TOP + rows_height) for hour in hours)
    hour_labels = "".join(
        _render_hour_label(hour, ledger, axis) for hour in hours if _is_clear_of_end_labels(hour, ledger)
    )
    bands = "".join(_render_halt(halt, ledger, rows_height) for halt in ledger["halts"])
    rows = "".join(_render_row(task, index, ledger) for index, task in enumerate(ledger["tasks"]))
    return (
        f'<figure class="panel pad chart"><svg viewBox="0 0 {CHART_WIDTH} {axis + BOTTOM_MARGIN}" role="img"'
        f' aria-label="How the wave {escape(ledger["wave"])} went">{grid}{bands}{rows}'
        f'<text class="g-text" x="{LABEL_WIDTH}" y="{axis}">{format_clock(ledger["first"])}</text>{hour_labels}'
        f'<text class="g-text" x="{TRACK_END}" y="{axis}" text-anchor="end">{format_clock(ledger["last"])}</text>'
        f"</svg>{render_legend(LEGEND)}</figure>"
    )
