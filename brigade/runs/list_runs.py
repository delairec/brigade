import json
import os
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.runs.run_locations import PID_FILE, RESULT_FILE, RUN_RECORD_FILE, RUNS_DIRECTORY
from brigade.runs.run_record import RUN_RECORD_SHAPE, RunRecord
from brigade.runs.run_result import RUN_RESULT_SHAPE, RunResult
from brigade.system.validate_document import DocumentInvalid, validate_document

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


def _read_validated(path: Path, kind_name: str, shape: dict) -> dict:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        raise BrigadeError(f"{path} is not a {kind_name}: not a JSON document") from None
    try:
        validate_document(document, shape)
    except DocumentInvalid as problem:
        raise BrigadeError(f"{path} is not a {kind_name}: {problem}") from None
    return document


def _describe_run(run_directory: Path) -> dict:
    record = RunRecord.from_document(_read_validated(run_directory / RUN_RECORD_FILE, "run record", RUN_RECORD_SHAPE))
    result_path = run_directory / RESULT_FILE
    if result_path.exists():
        state = "finished"
        outcome = RunResult.from_document(_read_validated(result_path, "run result", RUN_RESULT_SHAPE)).outcome
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


def list_runs(state_root: Path) -> list[dict]:
    runs_directory = state_root / RUNS_DIRECTORY
    if not runs_directory.is_dir():
        return []
    run_directories = sorted(path for path in runs_directory.iterdir() if (path / RUN_RECORD_FILE).is_file())
    return [_describe_run(run_directory) for run_directory in run_directories]
