from brigade.runs.create_run_directory import create_run_directory
from brigade.runs.detach_run import detach_run
from brigade.runs.plan_run import RunPlan, RunRequest, plan_run
from brigade.runs.run_segments import run_segments

DOCUMENT_SCHEMA_VERSION = 1


def _read_run_request(request) -> RunRequest:
    return RunRequest(
        procedure=request.procedure,
        slot=request.slot,
        project=request.project,
        cwd=request.cwd,
        brief=request.brief,
        arguments=tuple(request.arguments),
        run_id=request.run_id,
    )


def _attach_warnings(document: dict, plan: RunPlan) -> dict:
    if not plan.warnings:
        return document
    return {**document, "warnings": list(plan.warnings)}


def run(request, runtime) -> dict:
    plan = plan_run(_read_run_request(request), runtime)
    create_run_directory(plan)
    if request.detach:
        pid = detach_run(plan, runtime)
        return _attach_warnings({"schema_version": DOCUMENT_SCHEMA_VERSION, "run": plan.run_id, "pid": pid}, plan)
    records = run_segments(plan, runtime)
    document = {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "run": plan.run_id,
        "procedure": plan.procedure.name,
        "slot": plan.slot,
        "role": plan.role.role,
        "client": plan.client,
        "project": plan.project,
        "segments": len(records),
        "outcome": records[-1].result["outcome"],
    }
    return _attach_warnings(document, plan)
