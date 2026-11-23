from pathlib import Path

from brigade.errors import BrigadeError
from brigade.runs.describe_run import describe_run
from brigade.runs.journal_reader import JournalReader
from brigade.runs.list_segments import list_segments
from brigade.runs.read_run_document import read_run_document
from brigade.runs.read_run_finished import read_run_finished
from brigade.runs.run_locations import JOURNAL_FILE, RESULT_FILE, RUN_RECORD_FILE, RUNS_DIRECTORY
from brigade.runs.run_record import RUN_RECORD_SHAPE, RunRecord

DOCUMENT_SCHEMA_VERSION = 1


def _read_message(run_directory: Path) -> str | None:
    result_path = run_directory / RESULT_FILE
    if not result_path.exists():
        return None
    return read_run_finished(result_path, "run result").message


def show_run(state_root: Path, run_id: str, *, with_journal: bool) -> dict:
    run_directory = state_root / RUNS_DIRECTORY / run_id
    if Path(run_id).name != run_id or not (run_directory / RUN_RECORD_FILE).is_file():
        raise BrigadeError(f"no run {run_id}")
    segments = list_segments(run_directory)
    record = RunRecord.from_document(read_run_document(run_directory / RUN_RECORD_FILE, "run record", RUN_RECORD_SHAPE))
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "run": {**describe_run(run_directory), "message": _read_message(run_directory)},
        "arguments": record.arguments,
        "segments": segments,
        "log": JournalReader(run_directory / JOURNAL_FILE).read_whole_records() if with_journal else None,
    }
