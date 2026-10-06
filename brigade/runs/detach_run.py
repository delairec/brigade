import sys

from brigade.runs.plan_run import RunPlan
from brigade.runs.run_locations import DETACHED_LOG_FILE, PID_FILE
from brigade.system.spawn_process import SpawnRequest, spawn_process

ARGUMENT_SEPARATOR = "="
NO_EXTRA_VARIABLES = {}


def _repeat_options(plan: RunPlan) -> tuple[str, ...]:
    project = ("--project", plan.project) if plan.project is not None else ()
    brief = ("--brief", str(plan.brief_path)) if plan.brief_path is not None else ()
    return ("--slot", plan.slot, "--cwd", str(plan.cwd), *project, *brief, "--run-id", plan.run_id)


def detach_run(plan: RunPlan, runtime) -> int:
    arguments = tuple(f"{key}{ARGUMENT_SEPARATOR}{value}" for key, value in plan.arguments.items())
    command = ("run", plan.procedure.argument, *arguments, *_repeat_options(plan))
    log = plan.run_directory / DETACHED_LOG_FILE
    process = spawn_process(
        SpawnRequest(
            argv=(sys.executable, str(runtime.entry_point), *command),
            cwd=str(plan.cwd),
            environment=NO_EXTRA_VARIABLES,
            stdin=None,
            stdout=log,
            stderr=log,
        )
    )
    (plan.run_directory / PID_FILE).write_text(f"{process.pid}\n", encoding="utf-8")
    return process.pid
