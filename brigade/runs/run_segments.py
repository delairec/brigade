from datetime import timedelta

from brigade.git.add_detached_worktree import add_detached_worktree
from brigade.git.remove_worktree import remove_worktree
from brigade.ledger.append_event import LedgerEvent, append_event
from brigade.ledger.declared_events import RUN_FINISHED
from brigade.runs.plan_run import RunPlan
from brigade.runs.run_locations import PROGRESS_FILE, RESULT_FILE
from brigade.runs.run_segment import WALL_LIMIT_OUTCOME, SegmentRecord, run_segment
from brigade.runtime import Runtime
from brigade.system.write_json_atomically import write_json_atomically

SIGNAL_RECORDED = "signal.recorded"
BUDGET_REACHED = "budget_reached"
TURN_LIMIT = "turn_limit"
DONE_OUTCOME = "done"
NO_FAILURE = "the run did not fail"
NO_ERROR_CLASS = "the client reported no error class"
NOT_IN_A_WAVE = "not launched by a wave"
CUT = "cut at the wall-time limit"
CUT_FIELDS = ("session", "steps", "usage", "error_class", "exit")


def _ends_on_budget(record: SegmentRecord) -> bool:
    return record.result["error_class"] == TURN_LIMIT or record.result["outcome"] == WALL_LIMIT_OUTCOME


def _holds_progress(plan: RunPlan) -> bool:
    return bool((plan.run_directory / PROGRESS_FILE).read_text(encoding="utf-8").strip())


def _explain_client_nulls(plan: RunPlan, fields: dict) -> dict:
    reasons = {
        "session": "the client reported no session",
        "steps": "the client reported no step count" if plan.counts_steps else "the client counts no steps",
        "usage": "the client reported no usage",
        "error_class": NO_FAILURE if fields["outcome"] == DONE_OUTCOME else NO_ERROR_CLASS,
    }
    return {key: reason for key, reason in reasons.items() if fields[key] is None}


def _explain_nulls(plan: RunPlan, fields: dict) -> dict:
    nulls = {}
    if fields["project"] is None:
        nulls["project"] = "no project given"
    nulls["wave"] = NOT_IN_A_WAVE
    nulls["task"] = NOT_IN_A_WAVE
    if fields["outcome"] == WALL_LIMIT_OUTCOME:
        return {**nulls, **{key: CUT for key in CUT_FIELDS}}
    return {**nulls, **_explain_client_nulls(plan, fields)}


def _describe_finished(plan: RunPlan, record: SegmentRecord) -> dict:
    result = record.result
    fields = {
        "run": plan.run_id,
        "segment": record.number,
        "procedure": plan.procedure.name,
        "slot": plan.slot,
        "role": plan.role.role,
        "client": plan.client,
        "project": plan.project,
        "session": result["session_id"],
        "steps": result["steps"] if plan.counts_steps else None,
        "duration_ms": record.measured_ms if result["duration_ms"] is None else result["duration_ms"],
        "usage": result["usage"],
        "outcome": result["outcome"],
        "error_class": result["error_class"],
        "exit": record.exit_code,
        "wave": None,
        "task": None,
    }
    return {**fields, "nulls": _explain_nulls(plan, fields)}


def _describe_signal(plan: RunPlan, record: SegmentRecord) -> dict:
    return {
        "signal": BUDGET_REACHED,
        "project": plan.project,
        "procedure": plan.procedure.name,
        "run": plan.run_id,
        "segment": record.number,
        "budget": plan.procedure.budget,
    }


def _run_with_handovers(plan: RunPlan, runtime: Runtime) -> list[SegmentRecord]:
    records = []
    instant = runtime.now
    while True:
        record = run_segment(plan, len(records) + 1, runtime)
        records.append(record)
        instant += timedelta(milliseconds=record.measured_ms)
        append_event(runtime.paths.state_root, LedgerEvent(RUN_FINISHED, instant, _describe_finished(plan, record)))
        if not _ends_on_budget(record):
            return records
        append_event(runtime.paths.state_root, LedgerEvent(SIGNAL_RECORDED, instant, _describe_signal(plan, record)))
        if record.number > plan.handovers or not _holds_progress(plan):
            return records


def run_segments(plan: RunPlan, runtime: Runtime) -> list[SegmentRecord]:
    if plan.disposable_worktree:
        add_detached_worktree(runtime.run_process, plan.cwd, plan.worktree)
    try:
        records = _run_with_handovers(plan, runtime)
    finally:
        if plan.disposable_worktree:
            remove_worktree(runtime.run_process, plan.cwd, plan.worktree)
    write_json_atomically(plan.run_directory / RESULT_FILE, records[-1].result)
    return records
