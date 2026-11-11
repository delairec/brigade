from pathlib import Path

from brigade.runs.read_run_document import read_run_document
from brigade.runs.run_locations import RUN_RECORD_FILE
from brigade.runs.run_record import RUN_RECORD_SHAPE
from brigade.system.paths import Paths


def locate_source_worktree(paths: Paths, root: Path) -> Path:
    if paths.run_directory is None:
        return root
    record = read_run_document(paths.run_directory / RUN_RECORD_FILE, "run record", RUN_RECORD_SHAPE)
    if record["worktree"] != str(root):
        return root
    return Path(record["cwd"])
