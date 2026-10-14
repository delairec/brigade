from pathlib import Path

from brigade.errors import BrigadeError
from brigade.runs.describe_run import describe_run
from brigade.runs.journal_reader import JournalReader
from brigade.runs.read_run_document import read_run_document
from brigade.runs.read_run_finished import read_run_finished
from brigade.runs.run_locations import JOURNAL_FILE, RESULT_FILE, RUN_RECORD_FILE, RUNS_DIRECTORY, SEGMENTS_DIRECTORY
from brigade.runs.run_record import RUN_RECORD_SHAPE, RunRecord

DOCUMENT_SCHEMA_VERSION = 1


def _describe_segment(segment_directory: Path, record: RunRecord) -> dict:
    number = _read_segment_number(segment_directory)
    result_path = segment_directory / RESULT_FILE
    if not result_path.exists():
        return {"segment": number, "outcome": None, "steps": None, "duration_ms": None}
    finished = read_run_finished(result_path, "segment result", record, number)
    return {
        "segment": number,
        "outcome": finished.outcome,
        "steps": finished.main_steps,
        "duration_ms": finished.duration_ms,
    }


def _read_segment_number(segment_directory: Path) -> int:
    return int(segment_directory.name)


def _list_segments(run_directory: Path, record: RunRecord) -> list[dict]:
    segments_directory = run_directory / SEGMENTS_DIRECTORY
    if not segments_directory.is_dir():
        return []
    return [_describe_segment(path, record) for path in sorted(segments_directory.iterdir(), key=_read_segment_number)]


def _read_message(run_directory: Path, record: RunRecord, segments: list[dict]) -> str | None:
    result_path = run_directory / RESULT_FILE
    if not result_path.exists():
        return None
    return read_run_finished(result_path, "run result", record, segments[-1]["segment"]).message


def show_run(state_root: Path, run_id: str, *, with_journal: bool) -> dict:
    run_directory = state_root / RUNS_DIRECTORY / run_id
    if Path(run_id).name != run_id or not (run_directory / RUN_RECORD_FILE).is_file():
        raise BrigadeError(f"no run {run_id}")
    record = RunRecord.from_document(read_run_document(run_directory / RUN_RECORD_FILE, "run record", RUN_RECORD_SHAPE))
    segments = _list_segments(run_directory, record)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "run": {**describe_run(run_directory), "message": _read_message(run_directory, record, segments)},
        "segments": segments,
        "journal": JournalReader(run_directory / JOURNAL_FILE).read_whole_records() if with_journal else None,
    }
