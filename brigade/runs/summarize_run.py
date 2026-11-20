from pathlib import Path

from brigade.runs.describe_run import describe_run
from brigade.runs.list_segments import list_segments
from brigade.runs.read_run_document import read_run_document
from brigade.runs.run_locations import RUN_RECORD_FILE
from brigade.runs.run_record import RUN_RECORD_SHAPE, RunRecord

LISTED_SEGMENT_FIELDS = ("segment", "outcome", "turns", "duration_ms")


def _sum_carried(segments: list[dict], measure: str) -> int | float | None:
    carried = [segment[measure] for segment in segments if segment[measure] is not None]
    return sum(carried) if carried else None


def _is_partial(segments: list[dict], measure: str) -> bool:
    return any(segment[measure] is None for segment in segments)


def summarize_run(run_directory: Path) -> dict:
    described = describe_run(run_directory)
    record = RunRecord.from_document(read_run_document(run_directory / RUN_RECORD_FILE, "run record", RUN_RECORD_SHAPE))
    segments = list_segments(run_directory)
    return {
        **described,
        "arguments": record.arguments,
        "segments": [{field: segment[field] for field in LISTED_SEGMENT_FIELDS} for segment in segments],
        "duration_ms": _sum_carried(segments, "duration_ms"),
        "cost_usd": _sum_carried(segments, "cost_usd"),
        "duration_partial": _is_partial(segments, "duration_ms"),
        "cost_partial": _is_partial(segments, "cost_usd"),
    }
