import os
from pathlib import Path

from brigade.runs.read_run_document import read_run_document
from brigade.runs.run_locations import PID_FILE, RESULT_FILE, RUN_RECORD_FILE
from brigade.runs.run_record import RUN_RECORD_SHAPE, RunRecord
from brigade.runs.run_result import RUN_RESULT_SHAPE, RunResult

NO_SIGNAL = 0


def _read_pid(run_directory: Path) -> int | None:
    try:
        text = (run_directory / PID_FILE).read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    if not text.isdigit():
        return None
    return int(text)


def _is_alive(pid: int | None) -> bool:
    if pid is None:
        return False
    try:
        os.kill(pid, NO_SIGNAL)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def describe_run(run_directory: Path) -> dict:
    record = RunRecord.from_document(read_run_document(run_directory / RUN_RECORD_FILE, "run record", RUN_RECORD_SHAPE))
    result_path = run_directory / RESULT_FILE
    if result_path.exists():
        state = "finished"
        outcome = RunResult.from_document(read_run_document(result_path, "run result", RUN_RESULT_SHAPE)).outcome
    else:
        state = "running" if _is_alive(_read_pid(run_directory)) else "dead"
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
