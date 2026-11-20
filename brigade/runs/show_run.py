from datetime import UTC, datetime, timedelta
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.ledger.run_finished import RunFinished
from brigade.runs.describe_run import describe_run
from brigade.runs.journal_reader import JournalReader
from brigade.runs.read_run_document import read_run_document
from brigade.runs.read_run_finished import RUN_FINISHED_SHAPE, read_run_finished
from brigade.runs.run_locations import JOURNAL_FILE, RESULT_FILE, RUN_RECORD_FILE, RUNS_DIRECTORY, SEGMENTS_DIRECTORY
from brigade.runs.run_record import RUN_RECORD_SHAPE, RunRecord
from brigade.system.instant_formats import ISO_INSTANT_FORMAT

DOCUMENT_SCHEMA_VERSION = 1
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


def _list_segments(run_directory: Path) -> list[dict]:
    segments_directory = run_directory / SEGMENTS_DIRECTORY
    if not segments_directory.is_dir():
        return []
    return [_describe_segment(path) for path in sorted(segments_directory.iterdir(), key=_read_segment_number)]


def _read_message(run_directory: Path) -> str | None:
    result_path = run_directory / RESULT_FILE
    if not result_path.exists():
        return None
    return read_run_finished(result_path, "run result").message


def show_run(state_root: Path, run_id: str, *, with_journal: bool) -> dict:
    run_directory = state_root / RUNS_DIRECTORY / run_id
    if Path(run_id).name != run_id or not (run_directory / RUN_RECORD_FILE).is_file():
        raise BrigadeError(f"no run {run_id}")
    segments = _list_segments(run_directory)
    record = RunRecord.from_document(read_run_document(run_directory / RUN_RECORD_FILE, "run record", RUN_RECORD_SHAPE))
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "run": {**describe_run(run_directory), "message": _read_message(run_directory)},
        "arguments": record.arguments,
        "segments": segments,
        "log": JournalReader(run_directory / JOURNAL_FILE).read_whole_records() if with_journal else None,
    }
