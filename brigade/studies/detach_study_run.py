import sys

from brigade.runs.record_run_pid import record_run_pid
from brigade.runs.run_locations import DETACHED_LOG_FILE, RUNS_DIRECTORY
from brigade.runtime import Runtime
from brigade.system.process_trace import SPAWNED, ProcessTrace
from brigade.system.spawn_process import SpawnRequest

NO_EXTRA_VARIABLES = {}


def detach_study_run(runtime: Runtime, study: str, run_id: str) -> int:
    run_directory = runtime.paths.state_root / RUNS_DIRECTORY / run_id
    log = run_directory / DETACHED_LOG_FILE
    request = SpawnRequest(
        argv=(sys.executable, str(runtime.entry_point), "study", "run", study, "--run-id", run_id),
        cwd=str(runtime.paths.config_root),
        environment=NO_EXTRA_VARIABLES,
        stdin=None,
        stdout=log,
        stderr=log,
    )
    process = runtime.spawn_process(request)
    runtime.trail.append(
        ProcessTrace(request.argv, request.cwd, SPAWNED, exit_code=None, duration_ms=None, pid=process.pid)
    )
    record_run_pid(run_directory, process.pid)
    return process.pid
