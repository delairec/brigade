import dataclasses
import json
from pathlib import Path

from brigade.ledger.declared_events import RUN_FINISHED_SCHEMA_VERSION
from tests.unit.ledger.create_run_finished import create_run_finished


def create_run_record(run_id: str) -> dict:
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
    path.write_text(json.dumps(create_run_record(run_directory.name)))
    return path


def write_run_result(
    path: Path,
    outcome: str = "done",
    *,
    message: str | None = None,
    session: str | None = None,
    main_steps: int | None = None,
) -> Path:
    finished = dataclasses.replace(
        create_run_finished(path.parent.name, outcome=outcome, main_steps=main_steps), message=message, session=session
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema_version": RUN_FINISHED_SCHEMA_VERSION, **finished.to_document()}))
    return path
