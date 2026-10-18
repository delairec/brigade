from pathlib import Path

from brigade.runs.is_recorded_process_alive import is_recorded_process_alive
from brigade.runs.read_run_document import read_run_document
from brigade.runs.read_run_finished import read_run_finished
from brigade.runs.run_locations import RESULT_FILE, RUN_RECORD_FILE
from brigade.runs.run_record import RUN_RECORD_SHAPE, RunRecord


def describe_run(run_directory: Path) -> dict:
    record = RunRecord.from_document(read_run_document(run_directory / RUN_RECORD_FILE, "run record", RUN_RECORD_SHAPE))
    result_path = run_directory / RESULT_FILE
    if result_path.exists():
        state = "finished"
        outcome = read_run_finished(result_path, "run result").outcome
    else:
        state = "running" if is_recorded_process_alive(run_directory) else "dead"
        outcome = None
    return {
        "run": record.run,
        "procedure": record.procedure,
        "slot": record.slot,
        "role": record.role,
        "project": record.project,
        "worktree": record.worktree,
        "state": state,
        "outcome": outcome,
        "wave": record.wave,
        "task": record.task,
    }
