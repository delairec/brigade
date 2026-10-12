from pathlib import Path

from brigade.errors import BrigadeError
from brigade.runs.describe_run import describe_run
from brigade.runs.journal_reader import JournalReader
from brigade.runs.read_run_document import read_run_document
from brigade.runs.run_locations import JOURNAL_FILE, RESULT_FILE, RUN_RECORD_FILE, RUNS_DIRECTORY, SEGMENTS_DIRECTORY
from brigade.runs.run_result import RUN_RESULT_SHAPE, RunResult

DOCUMENT_SCHEMA_VERSION = 1


def _describe_segment(segment_directory: Path) -> dict:
    result_path = segment_directory / RESULT_FILE
    outcome = None
    if result_path.exists():
        outcome = RunResult.from_document(read_run_document(result_path, "segment result", RUN_RESULT_SHAPE)).outcome
    return {"segment": int(segment_directory.name), "outcome": outcome}


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
    return RunResult.from_document(read_run_document(result_path, "run result", RUN_RESULT_SHAPE)).message


def show_run(state_root: Path, run_id: str, with_journal: bool) -> dict:
    run_directory = state_root / RUNS_DIRECTORY / run_id
    if Path(run_id).name != run_id or not (run_directory / RUN_RECORD_FILE).is_file():
        raise BrigadeError(f"no run {run_id}")
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "run": {**describe_run(run_directory), "message": _read_message(run_directory)},
        "segments": _list_segments(run_directory),
        "journal": JournalReader(run_directory / JOURNAL_FILE).read_whole_records() if with_journal else None,
    }
