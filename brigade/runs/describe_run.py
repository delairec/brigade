from pathlib import Path

from brigade.runs.read_run_document import read_run_document
from brigade.runs.read_run_pid import read_run_pid
from brigade.runs.run_locations import RESULT_FILE, RUN_RECORD_FILE
from brigade.runs.run_record import RUN_RECORD_SHAPE, RunRecord
from brigade.runs.run_result import RUN_RESULT_SHAPE, RunResult
from brigade.system.is_process_alive import is_process_alive


def describe_run(run_directory: Path) -> dict:
    record = RunRecord.from_document(read_run_document(run_directory / RUN_RECORD_FILE, "run record", RUN_RECORD_SHAPE))
    result_path = run_directory / RESULT_FILE
    if result_path.exists():
        state = "finished"
        outcome = RunResult.from_document(read_run_document(result_path, "run result", RUN_RESULT_SHAPE)).outcome
    else:
        pid = read_run_pid(run_directory)
        state = "running" if pid is not None and is_process_alive(pid) else "dead"
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
