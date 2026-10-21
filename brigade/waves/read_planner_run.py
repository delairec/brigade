from pathlib import Path

from brigade.errors import BrigadeError
from brigade.runs.describe_run import describe_run
from brigade.runs.read_run_document import read_run_document
from brigade.runs.run_locations import RUN_RECORD_FILE, RUNS_DIRECTORY
from brigade.runs.run_record import RUN_RECORD_SHAPE

PLANNER_PROCEDURE = "wave-plan"
PLANNER_STATES = {"running": "live", "dead": "dead"}


def _is_planner_of(run_directory: Path, request: str) -> bool:
    if not (run_directory / RUN_RECORD_FILE).is_file():
        return False
    try:
        record = read_run_document(run_directory / RUN_RECORD_FILE, "run record", RUN_RECORD_SHAPE)
    except BrigadeError:
        return False
    return record["procedure"] == PLANNER_PROCEDURE and record["arguments"].get("request") == request


def read_planner_run(state_root: Path, request: str) -> dict | None:
    runs_directory = state_root / RUNS_DIRECTORY
    if not runs_directory.is_dir():
        return None
    planners = [path for path in sorted(runs_directory.iterdir()) if _is_planner_of(path, request)]
    if not planners:
        return None
    described = describe_run(planners[-1])
    return {"run": described["run"], "state": PLANNER_STATES.get(described["state"], described["outcome"])}
