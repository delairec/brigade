import json
from collections.abc import Callable
from pathlib import Path

from brigade.runs.run_locations import RUN_RECORD_FILE, RUNS_DIRECTORY


def is_run_live_on(state_root: Path, worktree: Path, is_alive: Callable[[Path], bool]) -> bool:
    return any(
        json.loads(record.read_text(encoding="utf-8"))["cwd"] == str(worktree) and is_alive(record.parent)
        for record in (state_root / RUNS_DIRECTORY).glob(f"*/{RUN_RECORD_FILE}")
    )
