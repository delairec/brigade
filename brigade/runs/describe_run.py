from pathlib import Path

from brigade.runs.read_run_document import read_run_document
from brigade.runs.read_run_finished import read_run_finished
from brigade.runs.read_run_pid import read_run_pid
from brigade.runs.run_locations import RESULT_FILE, RUN_RECORD_FILE, SEGMENTS_DIRECTORY
from brigade.runs.run_record import RUN_RECORD_SHAPE, RunRecord
from brigade.system.read_process_identity import read_process_identity


def _read_last_segment_number(run_directory: Path) -> int:
    return max(int(path.name) for path in (run_directory / SEGMENTS_DIRECTORY).iterdir())


def describe_run(run_directory: Path) -> dict:
    record = RunRecord.from_document(read_run_document(run_directory / RUN_RECORD_FILE, "run record", RUN_RECORD_SHAPE))
    result_path = run_directory / RESULT_FILE
    if result_path.exists():
        state = "finished"
        last_segment = _read_last_segment_number(run_directory)
        outcome = read_run_finished(result_path, "run result", record, last_segment).outcome
    else:
        recorded = read_run_pid(run_directory)
        alive = recorded is not None and read_process_identity(recorded.pid) == recorded.identity
        state = "running" if alive else "dead"
        outcome = None
    return {
        "run": record.run,
        "procedure": record.procedure,
        "slot": record.slot,
        "role": record.role,
        "project": record.project,
        "state": state,
        "outcome": outcome,
    }
