from pathlib import Path

from brigade.runs.describe_run import describe_run
from brigade.runs.run_locations import RUN_RECORD_FILE, RUNS_DIRECTORY


def list_runs(state_root: Path) -> list[dict]:
    runs_directory = state_root / RUNS_DIRECTORY
    if not runs_directory.is_dir():
        return []
    run_directories = sorted(path for path in runs_directory.iterdir() if (path / RUN_RECORD_FILE).is_file())
    return [describe_run(run_directory) for run_directory in run_directories]
