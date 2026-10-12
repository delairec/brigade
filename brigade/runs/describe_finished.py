import dataclasses

from brigade.ledger.run_finished import RunFinished
from brigade.runs.plan_run import RunPlan
from brigade.runs.run_segment import (
    NO_SESSION_AT_LAUNCH,
    NOT_LAUNCHED,
    STOPPED_BY_A_SIGNAL,
    STOPPED_OUTCOME,
    WALL_LIMIT_OUTCOME,
    SegmentRecord,
)

DONE_OUTCOME = "done"
NO_FAILURE = "the run did not fail"
NO_ERROR_CLASS = "the client reported no error class"
NOT_IN_A_WAVE = "not launched by a wave"
WALL_LIMIT_CUT = "cut at the wall-time limit"
NO_NULLS_EXPLAINED = {}
ENDING_REASONS = {WALL_LIMIT_OUTCOME: WALL_LIMIT_CUT, STOPPED_OUTCOME: STOPPED_BY_A_SIGNAL}


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


def _explain_ending_nulls(record: SegmentRecord, finished: RunFinished, ending_reason: str) -> dict:
    reasons = {
        "session": NO_SESSION_AT_LAUNCH,
        "main_steps": record.uncounted,
        "total_steps": record.uncounted,
        "usage": record.uncounted,
        "error_class": ending_reason,
        "exit": ending_reason,
    }
    return {field: reason for field, reason in reasons.items() if getattr(finished, field) is None}


def _choose_ending_reason(record: SegmentRecord, finished: RunFinished) -> str | None:
    if finished.outcome in ENDING_REASONS:
        return ENDING_REASONS[finished.outcome]
    if record.uncounted == NOT_LAUNCHED:
        return record.result.message
    return None


def _explain_nulls(plan: RunPlan, record: SegmentRecord, finished: RunFinished) -> dict:
    nulls = {}
    if finished.project is None:
        nulls["project"] = "no project given"
    nulls["wave"] = NOT_IN_A_WAVE
    nulls["task"] = NOT_IN_A_WAVE
    ending_reason = _choose_ending_reason(record, finished)
    if ending_reason is None:
        return {**nulls, **_explain_client_nulls(plan, record, finished)}
    return {**nulls, **_explain_ending_nulls(record, finished, ending_reason)}


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
