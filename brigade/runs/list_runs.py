import json
import os
from pathlib import Path

from brigade.runs.run_locations import PID_FILE, RESULT_FILE, RUN_RECORD_FILE, RUNS_DIRECTORY

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


def _describe_run(run_directory: Path) -> dict:
    record = json.loads((run_directory / RUN_RECORD_FILE).read_text(encoding="utf-8"))
    result_path = run_directory / RESULT_FILE
    if result_path.exists():
        state = "finished"
        outcome = json.loads(result_path.read_text(encoding="utf-8"))["outcome"]
    else:
        state = "running" if _is_alive(_read_pid(run_directory)) else "dead"
        outcome = None
    return {
        "run": record["run"],
        "procedure": record["procedure"],
        "slot": record["slot"],
        "role": record["role"],
        "project": record["project"],
        "state": state,
        "outcome": outcome,
    }


def list_runs(state_root: Path) -> list[dict]:
    runs_directory = state_root / RUNS_DIRECTORY
    if not runs_directory.is_dir():
        return []
    run_directories = sorted(path for path in runs_directory.iterdir() if (path / RUN_RECORD_FILE).is_file())
    return [_describe_run(run_directory) for run_directory in run_directories]
