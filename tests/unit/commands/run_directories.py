import json
from pathlib import Path

FIRST_RUN = "20261007T090000Z-b70a01"
SECOND_RUN = "20261008T090000Z-c80b02"


def create_run_record(run_id: str, wave: str | None, task: str | None) -> dict:
    return {
        "schema_version": 1,
        "run": run_id,
        "procedure": "deliver",
        "procedure_path": "built-in",
        "slot": "build",
        "role": "builder",
        "role_source": "built-in",
        "client": "fake",
        "project": None,
        "cwd": "/home/user/tidepool",
        "worktree": "/home/user/tidepool",
        "capabilities": ["read"],
        "budget": 40,
        "wall_limit_s": 1500.0,
        "arguments": {},
        "wave": wave,
        "task": task,
        "brief": None,
    }


def create_run_result(run_id: str, outcome: str, ts: str) -> dict:
    return {
        "schema_version": 2,
        "ts": ts,
        "event": "run.finished",
        "run": run_id,
        "segment": 1,
        "procedure": "deliver",
        "slot": "build",
        "role": "builder",
        "client": "fake",
        "project": None,
        "session": "session-b74",
        "main_steps": 12,
        "total_steps": 12,
        "duration_ms": 4200,
        "usage": None,
        "outcome": outcome,
        "error_class": None,
        "exit": 0,
        "wave": None,
        "task": None,
        "nulls": {},
        "message": "the task is delivered",
    }


def write_run(state_root: Path, record: dict, result: dict | None) -> Path:
    run_directory = state_root / "runs" / record["run"]
    run_directory.mkdir(parents=True)
    (run_directory / "run.json").write_text(json.dumps(record), encoding="utf-8")
    if result is not None:
        (run_directory / "result.json").write_text(json.dumps(result), encoding="utf-8")
        (run_directory / "segments" / "1").mkdir(parents=True)
        (run_directory / "segments" / "1" / "result.json").write_text(json.dumps(result), encoding="utf-8")
    return run_directory


def create_planner_record(run_id: str, request: str) -> dict:
    return {
        **create_run_record(run_id, None, None),
        "procedure": "wave-plan",
        "slot": "plan",
        "role": "planner",
        "arguments": {"request": request},
    }
