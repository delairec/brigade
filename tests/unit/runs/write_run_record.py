import json
from pathlib import Path


def _describe_run(run_id: str) -> dict:
    return {
        "schema_version": 1,
        "run": run_id,
        "procedure": "build-task",
        "procedure_path": "built-in",
        "slot": "build",
        "role": "builder",
        "role_source": "built-in",
        "client": "fake",
        "project": None,
        "cwd": "/home/ada/tidepool",
        "worktree": "/home/ada/tidepool",
        "capabilities": ["read"],
        "budget": 40,
        "wall_limit_s": 1500.0,
        "arguments": {},
        "wave": None,
        "task": None,
        "brief": None,
    }


def write_run_record(run_directory: Path) -> Path:
    run_directory.mkdir(parents=True, exist_ok=True)
    path = run_directory / "run.json"
    path.write_text(json.dumps(_describe_run(run_directory.name)))
    return path
