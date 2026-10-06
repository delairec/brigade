import os

from brigade.roles.render_role_file import render_role_file
from brigade.runs.plan_run import RunPlan
from brigade.runs.record_run_pid import record_run_pid
from brigade.runs.run_locations import PROGRESS_FILE, ROLE_FILE, RUN_RECORD_FILE
from brigade.system.create_directory import create_directory
from brigade.system.write_json_atomically import write_json_atomically
from brigade.system.write_text_file import write_text_file

RECORD_SCHEMA_VERSION = 1


def _describe_run(plan: RunPlan) -> dict:
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "run": plan.run_id,
        "procedure": plan.procedure.name,
        "procedure_path": plan.procedure.location,
        "slot": plan.slot,
        "role": plan.role.role,
        "role_source": plan.role.source,
        "client": plan.client,
        "project": plan.project,
        "cwd": str(plan.cwd),
        "worktree": str(plan.worktree),
        "capabilities": list(plan.capabilities),
        "budget": plan.procedure.budget,
        "wall_limit_s": plan.wall_limit_s,
        "arguments": plan.arguments,
    }


def create_run_directory(plan: RunPlan) -> None:
    create_directory(plan.run_directory)
    write_json_atomically(plan.run_directory / RUN_RECORD_FILE, _describe_run(plan))
    record_run_pid(plan.run_directory, os.getpid())
    write_text_file(plan.run_directory / ROLE_FILE, render_role_file(plan.role.front_matter, plan.role.body))
    write_text_file(plan.run_directory / PROGRESS_FILE, "")
