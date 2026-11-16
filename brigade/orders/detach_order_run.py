from brigade.runs.detach_brigade_command import DetachedCommand, detach_brigade_command
from brigade.runs.record_run_pid import record_run_pid
from brigade.runs.run_locations import RUNS_DIRECTORY
from brigade.runtime import Runtime


def detach_order_run(runtime: Runtime, order: str, run_id: str) -> None:
    detached = DetachedCommand(
        command=("order", "run", order, "--run-id", run_id),
        cwd=str(runtime.paths.config_root),
        run_directory=runtime.paths.state_root / RUNS_DIRECTORY / run_id,
    )
    detach_brigade_command(runtime, detached, record_run_pid)
