from datetime import UTC, datetime, timedelta
from pathlib import Path

from brigade.ledger.run_finished import RunFinished
from brigade.runs.read_run_document import read_run_document
from brigade.runs.read_run_finished import RUN_FINISHED_SHAPE
from brigade.runs.run_locations import RESULT_FILE, SEGMENTS_DIRECTORY
from brigade.system.instant_formats import ISO_INSTANT_FORMAT

UNKNOWN_START = None


def _read_segment_start(result: dict) -> str | None:
    ended_at = result.get("ts")
    if ended_at is None or result["duration_ms"] is None:
        return UNKNOWN_START
    started = datetime.strptime(ended_at, ISO_INSTANT_FORMAT).replace(tzinfo=UTC) - timedelta(
        milliseconds=result["duration_ms"]
    )
    return started.strftime(ISO_INSTANT_FORMAT)


def _describe_segment(segment_directory: Path) -> dict:
    number = _read_segment_number(segment_directory)
    result_path = segment_directory / RESULT_FILE
    if not result_path.exists():
        return {
            "segment": number,
            "outcome": None,
            "turns": None,
            "duration_ms": None,
            "started_at": UNKNOWN_START,
            "cost_usd": None,
        }
    result = read_run_document(result_path, "segment result", RUN_FINISHED_SHAPE)
    finished = RunFinished.from_document(result)
    return {
        "segment": number,
        "outcome": finished.outcome,
        "turns": finished.main_turns,
        "duration_ms": finished.duration_ms,
        "started_at": _read_segment_start(result),
        "cost_usd": finished.cost_usd,
    }


def _read_segment_number(segment_directory: Path) -> int:
    return int(segment_directory.name)


def list_segments(run_directory: Path) -> list[dict]:
    segments_directory = run_directory / SEGMENTS_DIRECTORY
    if not segments_directory.is_dir():
        return []
    return [_describe_segment(path) for path in sorted(segments_directory.iterdir(), key=_read_segment_number)]
