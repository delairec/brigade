import dataclasses

from brigade.ledger.run_finished import RunFinished
from brigade.runs.plan_run import RunPlan
from brigade.runs.run_segment import WALL_LIMIT_CUT, WALL_LIMIT_OUTCOME, SegmentRecord

DONE_OUTCOME = "done"
NO_FAILURE = "the run did not fail"
NO_ERROR_CLASS = "the client reported no error class"
NOT_IN_A_WAVE = "not launched by a wave"
CUT_FIELDS = ("session", "main_steps", "total_steps", "usage", "error_class", "exit")
NO_NULLS_EXPLAINED = {}


def _explain_missing_main_steps(plan: RunPlan, record: SegmentRecord) -> str:
    client_reason = "the client reported no step count" if plan.counts_steps else "the client counts no steps"
    return f"{client_reason} and {record.uncounted}"


def _explain_client_nulls(plan: RunPlan, record: SegmentRecord, finished: RunFinished) -> dict:
    reasons = {
        "session": "the client reported no session",
        "main_steps": _explain_missing_main_steps(plan, record),
        "total_steps": record.uncounted,
        "usage": "the client reported no usage",
        "error_class": NO_FAILURE if finished.outcome == DONE_OUTCOME else NO_ERROR_CLASS,
    }
    return {field: reason for field, reason in reasons.items() if getattr(finished, field) is None}


def _explain_nulls(plan: RunPlan, record: SegmentRecord, finished: RunFinished) -> dict:
    nulls = {}
    if finished.project is None:
        nulls["project"] = "no project given"
    nulls["wave"] = NOT_IN_A_WAVE
    nulls["task"] = NOT_IN_A_WAVE
    if finished.outcome == WALL_LIMIT_OUTCOME:
        return {**nulls, **{field: WALL_LIMIT_CUT for field in CUT_FIELDS}}
    return {**nulls, **_explain_client_nulls(plan, record, finished)}


def _choose_main_steps(plan: RunPlan, record: SegmentRecord) -> int | None:
    if record.counted_steps is not None:
        return record.counted_steps.main_steps
    return record.result.steps if plan.counts_steps else None


def describe_finished(plan: RunPlan, record: SegmentRecord) -> RunFinished:
    result = record.result
    finished = RunFinished(
        run=plan.run_id,
        segment=record.number,
        procedure=plan.procedure.name,
        slot=plan.slot,
        role=plan.role.role,
        client=plan.client,
        project=plan.project,
        session=result.session_id,
        main_steps=_choose_main_steps(plan, record),
        total_steps=None if record.counted_steps is None else record.counted_steps.total_steps,
        duration_ms=record.measured_ms,
        usage=result.usage,
        outcome=result.outcome,
        error_class=result.error_class,
        exit=record.exit_code,
        wave=None,
        task=None,
        nulls=NO_NULLS_EXPLAINED,
        cost_usd=record.cost_usd,
    )
    return dataclasses.replace(finished, nulls=_explain_nulls(plan, record, finished))
