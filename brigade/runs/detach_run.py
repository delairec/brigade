from brigade.runs.detach_brigade_command import detach_brigade_command
from brigade.runs.plan_run import RunPlan
from brigade.runs.record_run_pid import record_run_pid
from brigade.runtime import Runtime

ARGUMENT_SEPARATOR = "="


def _repeat_options(plan: RunPlan) -> tuple[str, ...]:
    project = ("--project", plan.project) if plan.project is not None else ()
    brief = ("--brief", str(plan.brief_path)) if plan.brief_path is not None else ()
    wave = ("--wave", plan.wave) if plan.wave is not None else ()
    task = ("--task", plan.task) if plan.task is not None else ()
    resume = ("--resume",) if plan.resumed else ()
    return (
        "--slot",
        plan.slot,
        "--cwd",
        str(plan.cwd),
        *project,
        *brief,
        *wave,
        *task,
        "--run-id",
        plan.run_id,
        *resume,
    )


def detach_run(plan: RunPlan, runtime: Runtime) -> int:
    arguments = tuple(f"{key}{ARGUMENT_SEPARATOR}{value}" for key, value in plan.arguments.items())
    command = ("run", plan.procedure.argument, *arguments, *_repeat_options(plan))
    return detach_brigade_command(runtime, command, str(plan.cwd), plan.run_directory, record_run_pid)
