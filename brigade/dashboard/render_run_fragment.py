from html import escape

from brigade.dashboard.render_html_table import render_html_table
from brigade.runs.format_duration import format_duration

SUMMARY_FIELDS = ("procedure", "slot", "role", "project", "wave", "task", "worktree", "state", "outcome", "message")
SEGMENT_HEADER = ("segment", "outcome", "steps", "duration")
ABSENT = "-"
NO_SEGMENT = "no segment"


def _show(value: object) -> str:
    return ABSENT if value is None else escape(str(value))


def _render_segment(segment: dict) -> tuple[str, ...]:
    duration_ms = segment["duration_ms"]
    return (
        _show(segment["segment"]),
        _show(segment["outcome"]),
        _show(segment["steps"]),
        ABSENT if duration_ms is None else format_duration(duration_ms),
    )


def _render_progress(progress: dict | None) -> str:
    if progress is None:
        return ""
    return f"<h3>Progress</h3><pre>{escape(progress['text'])}</pre>"


def render_run_fragment(document: dict) -> str:
    run = document["run"]
    summary = "".join(f"<dt>{field}</dt><dd>{_show(run[field])}</dd>" for field in SUMMARY_FIELDS)
    segments = render_html_table(
        SEGMENT_HEADER, [_render_segment(segment) for segment in document["segments"]], NO_SEGMENT
    )
    return (
        f"<h2>Run {escape(run['run'])}</h2><dl>{summary}</dl>"
        f"<h3>Segments</h3>{segments}{_render_progress(document['progress'])}"
    )
