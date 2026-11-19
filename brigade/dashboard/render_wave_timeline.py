from datetime import datetime
from html import escape

from brigade.dashboard.read_state_tone import read_state_tone

LABEL_WIDTH = 20
TRACK_WIDTH = 100
ROW_HEIGHT = 12
MARK_RADIUS = 2
MILLISECONDS_PER_SECOND = 1000
SHORTEST_WAVE_MS = 1
TASK_STATE_EVENT = "task.state"


def _place(at: str, ledger: dict) -> float:
    elapsed = datetime.fromisoformat(at) - datetime.fromisoformat(ledger["first"])
    span = max(ledger["wall_time_ms"], SHORTEST_WAVE_MS)
    return LABEL_WIDTH + elapsed.total_seconds() * MILLISECONDS_PER_SECOND / span * TRACK_WIDTH


def _render_halt(halt: dict, ledger: dict, height: int) -> str:
    start = _place(halt["halted_at"], ledger)
    resumed_at = halt["resumed_at"]
    end = _place(resumed_at or ledger["last"], ledger)
    span = (
        f"from {halt['halted_at']}, not resumed" if resumed_at is None else f"from {halt['halted_at']} to {resumed_at}"
    )
    return (
        f'<rect class="halt-band" x="{start:g}" y="0" width="{end - start:g}" height="{height}">'
        f"<title>halted {escape(span)}</title></rect>"
    )


def _render_mark(event: dict, ledger: dict, row: int) -> str:
    fields = event["fields"]
    return (
        f'<circle class="timeline-mark tone-{read_state_tone(fields["state"])}" cx="{_place(event["at"], ledger):g}"'
        f' cy="{row}" r="{MARK_RADIUS}"><title>{escape(fields["task"])} {escape(fields["state"])} at'
        f" {escape(event['at'])}</title></circle>"
    )


def _render_row(task: str, index: int, ledger: dict) -> str:
    row = ROW_HEIGHT * index + ROW_HEIGHT // 2
    marks = "".join(
        _render_mark(event, ledger, row)
        for event in ledger["events"]
        if event["event"] == TASK_STATE_EVENT and event["fields"]["task"] == task
    )
    return f'<text class="timeline-label" x="0" y="{row}">{escape(task)}</text>{marks}'


def render_wave_timeline(ledger: dict) -> str:
    height = ROW_HEIGHT * len(ledger["tasks"])
    bands = "".join(_render_halt(halt, ledger, height) for halt in ledger["halts"])
    rows = "".join(_render_row(task, index, ledger) for index, task in enumerate(ledger["tasks"]))
    return (
        f'<svg class="timeline" viewBox="0 0 {LABEL_WIDTH + TRACK_WIDTH} {height}" role="img"'
        f' aria-label="How the wave {escape(ledger["wave"])} went">{bands}{rows}</svg>'
    )
