import dataclasses

from brigade.ledger.run_finished import RunFinished
from brigade.runs.plan_run import RunPlan
from brigade.runs.run_segment import (
    NO_SESSION_AT_LAUNCH,
    STOPPED_BY_A_SIGNAL,
    STOPPED_OUTCOME,
    WALL_LIMIT_OUTCOME,
    SegmentRecord,
)
from brigade.system.digest_text import digest_text

DONE_OUTCOME = "done"
NO_FAILURE = "the run did not fail"
NO_ERROR_CLASS = "the client reported no error class"
NOT_IN_A_WAVE = "not launched by a wave"
NOT_FOR_A_TASK = "not launched for a task"
WALL_LIMIT_CUT = "cut at the wall-time limit"
NO_EDIT_TOOL = "the client names no edit tool"
NO_EDIT = "the segment made no edit outside the progress file"
NO_DATED_CALL = "no dated tool call of the main transcript precedes the change to the worktree"
FIRST_EDIT_FIELDS = ("turns_to_first_edit", "tokens_to_first_edit")
NO_NULLS_EXPLAINED = {}
ENDING_REASONS = {WALL_LIMIT_OUTCOME: WALL_LIMIT_CUT, STOPPED_OUTCOME: STOPPED_BY_A_SIGNAL}


def _explain_missing_main_turns(plan: RunPlan, record: SegmentRecord) -> str:
    client_reason = "the client reported no turn count" if plan.counts_steps else "the client counts no turns"
    return f"{client_reason} and {record.uncounted}"


def _explain_client_nulls(plan: RunPlan, record: SegmentRecord, finished: RunFinished) -> dict:
    reasons = {
        "session": "the client reported no session",
        "main_turns": _explain_missing_main_turns(plan, record),
        "total_turns": record.uncounted,
        "usage": "the client reported no usage",
        "error_class": NO_FAILURE if finished.outcome == DONE_OUTCOME else NO_ERROR_CLASS,
    }
    return {field: reason for field, reason in reasons.items() if getattr(finished, field) is None}


def _explain_ending_nulls(record: SegmentRecord, finished: RunFinished, ending_reason: str) -> dict:
    reasons = {
        "session": NO_SESSION_AT_LAUNCH,
        "main_turns": record.uncounted,
        "total_turns": record.uncounted,
        "usage": record.uncounted,
        "error_class": ending_reason,
        "exit": ending_reason,
    }
    return {field: reason for field, reason in reasons.items() if getattr(finished, field) is None}


def _choose_ending_reason(record: SegmentRecord, finished: RunFinished) -> str | None:
    if finished.outcome in ENDING_REASONS:
        return ENDING_REASONS[finished.outcome]
    if record.adapter_failure is not None:
        return record.adapter_failure
    return None


def _explain_missing_first_edit(plan: RunPlan, record: SegmentRecord) -> dict:
    if record.first_edit is not None:
        return {}
    worktree = record.worktree
    if worktree.sampled and worktree.changed_at is None:
        reason = NO_EDIT
    elif not plan.edit_tools:
        reason = NO_EDIT_TOOL
    elif record.counted_steps is None:
        reason = record.uncounted
    elif worktree.changed_at is not None:
        reason = NO_DATED_CALL
    else:
        reason = NO_EDIT
    return dict.fromkeys(FIRST_EDIT_FIELDS, reason)


def _explain_nulls(plan: RunPlan, record: SegmentRecord, finished: RunFinished) -> dict:
    nulls = _explain_missing_first_edit(plan, record)
    if finished.project is None:
        nulls["project"] = "no project given"
    if finished.wave is None:
        nulls["wave"] = NOT_IN_A_WAVE
    if finished.task is None:
        nulls["task"] = NOT_FOR_A_TASK
    ending_reason = _choose_ending_reason(record, finished)
    if ending_reason is None:
        return {**nulls, **_explain_client_nulls(plan, record, finished)}
    return {**nulls, **_explain_ending_nulls(record, finished, ending_reason)}


def _choose_main_turns(plan: RunPlan, record: SegmentRecord) -> int | None:
    if record.counted_steps is not None:
        return record.counted_steps.main_turns
    return record.client_steps if plan.counts_steps else None


def describe_finished(plan: RunPlan, record: SegmentRecord) -> RunFinished:
    finished = RunFinished(
        run=plan.run_id,
        segment=record.number,
        procedure=plan.procedure.name,
        slot=plan.slot,
        role=plan.role.role,
        client=plan.client,
        project=plan.project,
        session=record.session_id,
        main_turns=_choose_main_turns(plan, record),
        total_turns=None if record.counted_steps is None else record.counted_steps.total_turns,
        duration_ms=record.measured_ms,
        usage=record.usage,
        outcome=record.outcome,
        error_class=record.error_class,
        exit=record.exit_code,
        wave=plan.wave,
        task=plan.task,
        nulls=NO_NULLS_EXPLAINED,
        cost_usd=record.cost_usd,
        message=record.message,
        reset=record.reset,
        turns_to_first_edit=None if record.first_edit is None else record.first_edit.steps,
        tokens_to_first_edit=None if record.first_edit is None else record.first_edit.tokens,
        role_digest=digest_text(plan.role.body),
        procedure_digest=digest_text(plan.procedure.body),
        shipped_budget=plan.budget.shipped,
    )
    return dataclasses.replace(finished, nulls=_explain_nulls(plan, record, finished))
