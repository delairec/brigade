from collections.abc import Callable
from pathlib import Path

from brigade.runs.detach_brigade_command import DetachedCommand, detach_brigade_command
from brigade.runs.run_locations import RUNS_DIRECTORY
from brigade.runtime import Runtime


def detach_study_run(runtime: Runtime, study: str, run_id: str, record_pid: Callable[[Path, int], None]) -> int:
    detached = DetachedCommand(
        command=("study", "run", study, "--run-id", run_id),
        cwd=str(runtime.paths.config_root),
        run_directory=runtime.paths.state_root / RUNS_DIRECTORY / run_id,
    )
    return detach_brigade_command(runtime, detached, record_pid)
