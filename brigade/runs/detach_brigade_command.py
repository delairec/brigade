import sys
from collections.abc import Callable
from pathlib import Path

from brigade.runs.run_locations import DETACHED_LOG_FILE
from brigade.runtime import Runtime
from brigade.system.process_trace import SPAWNED, ProcessTrace
from brigade.system.spawn_process import SpawnRequest

NO_EXTRA_VARIABLES = {}


def detach_brigade_command(
    runtime: Runtime,
    command: tuple[str, ...],
    cwd: str,
    run_directory: Path,
    record_pid: Callable[[Path, int], None],
) -> int:
    log = run_directory / DETACHED_LOG_FILE
    request = SpawnRequest(
        argv=(sys.executable, str(runtime.entry_point), *command),
        cwd=cwd,
        environment=NO_EXTRA_VARIABLES,
        stdin=None,
        stdout=log,
        stderr=log,
    )
    process = runtime.spawn_process(request)
    runtime.trail.append(
        ProcessTrace(request.argv, request.cwd, SPAWNED, exit_code=None, duration_ms=None, pid=process.pid)
    )
    record_pid(run_directory, process.pid)
    return process.pid
