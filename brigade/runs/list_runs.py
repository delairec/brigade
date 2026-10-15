from pathlib import Path

from brigade.errors import BrigadeError
from brigade.runs.describe_run import describe_run
from brigade.runs.run_locations import RUN_RECORD_FILE, RUNS_DIRECTORY


def list_runs(state_root: Path) -> dict:
    runs_directory = state_root / RUNS_DIRECTORY
    runs = []
    skipped = []
    if not runs_directory.is_dir():
        return {"runs": runs, "skipped": skipped}
    for run_directory in sorted(path for path in runs_directory.iterdir() if (path / RUN_RECORD_FILE).is_file()):
        try:
            runs.append(describe_run(run_directory))
        except BrigadeError as refusal:
            skipped.append({"run": run_directory.name, "reason": str(refusal)})
    return {"runs": runs, "skipped": skipped}
