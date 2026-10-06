import time
from dataclasses import dataclass
from typing import Optional

from brigade.runs.compose_brief import BriefParts, compose_brief
from brigade.runs.plan_run import RunPlan
from brigade.runs.run_locations import BRIEF_FILE, PROGRESS_FILE, SEGMENTS_DIRECTORY, STDERR_FILE, STDOUT_FILE
from brigade.system.ask_client import ClientQuestion
from brigade.system.ask_named_client import ask_named_client
from brigade.system.spawn_process import SpawnRequest, spawn_process
from brigade.system.wait_within_limit import wait_within_limit

REQUEST_SCHEMA_VERSION = 1
FIRST_SEGMENT = 1
PROGRESS_FILE_VARIABLE = "BRIGADE_PROGRESS_FILE"
WALL_LIMIT_OUTCOME = "wall_limit"


@dataclass(frozen=True)
class SegmentRecord:
    number: int
    result: dict
    exit_code: Optional[int]
    measured_ms: int


def _compose_segment_brief(plan: RunPlan, number: int) -> str:
    progress_file = plan.run_directory / PROGRESS_FILE
    progress = None if number == FIRST_SEGMENT else progress_file.read_text(encoding="utf-8")
    return compose_brief(
        BriefParts(
            progress=progress,
            procedure=plan.procedure.name,
            procedure_body=plan.procedure.body,
            arguments=plan.arguments,
            brief=plan.brief,
            progress_file=progress_file,
        )
    )


def _describe_role(plan: RunPlan) -> dict:
    return {
        "name": plan.role.role,
        "package": plan.role.body,
        "capabilities": list(plan.capabilities),
        "reasoning": plan.role.front_matter["reasoning"],
        "budget": plan.procedure.budget,
    }


def _ask_client(plan: RunPlan, runtime, operation: str, request: dict) -> dict:
    return ask_named_client(runtime, plan.configuration, ClientQuestion(plan.client, operation, request))


def _describe_cut(plan: RunPlan, measured_ms: int) -> dict:
    return {
        "schema_version": REQUEST_SCHEMA_VERSION,
        "outcome": WALL_LIMIT_OUTCOME,
        "steps": None,
        "usage": None,
        "session_id": None,
        "duration_ms": measured_ms,
        "error_class": None,
        "reset": None,
        "message": f"cut at the wall-time limit of {plan.wall_limit_s:g} s",
    }


def run_segment(plan: RunPlan, number: int, runtime) -> SegmentRecord:
    segment_directory = plan.run_directory / SEGMENTS_DIRECTORY / str(number)
    segment_directory.mkdir(parents=True, exist_ok=True)
    brief = _compose_segment_brief(plan, number)
    (segment_directory / BRIEF_FILE).write_text(brief, encoding="utf-8")
    launch = _ask_client(
        plan,
        runtime,
        "launch-argv",
        {
            "schema_version": REQUEST_SCHEMA_VERSION,
            "worktree": str(plan.worktree),
            "brief": brief,
            "role": _describe_role(plan),
        },
    )
    started = time.monotonic()
    process = spawn_process(
        SpawnRequest(
            argv=tuple(launch["argv"]),
            cwd=str(plan.worktree),
            environment={**launch["environment"], PROGRESS_FILE_VARIABLE: str(plan.run_directory / PROGRESS_FILE)},
            stdin=launch["stdin"],
            stdout=segment_directory / STDOUT_FILE,
            stderr=segment_directory / STDERR_FILE,
        )
    )
    exit_code = wait_within_limit(process, plan.wall_limit_s)
    measured_ms = round((time.monotonic() - started) * 1000)
    if exit_code is None:
        cut = _describe_cut(plan, measured_ms)
        return SegmentRecord(number=number, result=cut, exit_code=None, measured_ms=measured_ms)
    result = _ask_client(
        plan,
        runtime,
        "parse-result",
        {
            "schema_version": REQUEST_SCHEMA_VERSION,
            "exit_code": exit_code,
            "stdout": (segment_directory / STDOUT_FILE).read_text(encoding="utf-8", errors="replace"),
            "stderr": (segment_directory / STDERR_FILE).read_text(encoding="utf-8", errors="replace"),
        },
    )
    return SegmentRecord(number=number, result=result, exit_code=exit_code, measured_ms=measured_ms)
