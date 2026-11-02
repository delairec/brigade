import dataclasses
import sys
from collections.abc import Callable
from pathlib import Path

from brigade.runs.run_locations import DETACHED_LOG_FILE
from brigade.runtime import Runtime
from brigade.system.paths import SESSION_BUS_VARIABLE
from brigade.system.process_trace import SPAWNED, ProcessTrace
from brigade.system.spawn_process import SpawnRequest

NO_SESSION_BUS = None


@dataclasses.dataclass(frozen=True)
class DetachedCommand:
    command: tuple[str, ...]
    cwd: str
    run_directory: Path


def _carry_session_bus(session_bus_address: str | None) -> dict:
    if session_bus_address is NO_SESSION_BUS:
        return {}
    return {SESSION_BUS_VARIABLE: session_bus_address}


def detach_brigade_command(runtime: Runtime, detached: DetachedCommand, record_pid: Callable[[Path, int], None]) -> int:
    log = detached.run_directory / DETACHED_LOG_FILE
    request = SpawnRequest(
        argv=(sys.executable, str(runtime.entry_point), *detached.command),
        cwd=detached.cwd,
        environment=_carry_session_bus(runtime.paths.session_bus_address),
        stdin=None,
        stdout=log,
        stderr=log,
    )
    process = runtime.spawn_process(request)
    runtime.trail.append(
        ProcessTrace(request.argv, request.cwd, SPAWNED, exit_code=None, duration_ms=None, pid=process.pid)
    )
    record_pid(detached.run_directory, process.pid)
    return process.pid
