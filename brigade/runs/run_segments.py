from datetime import timedelta

from brigade.git.add_detached_worktree import add_detached_worktree
from brigade.git.remove_worktree import remove_worktree
from brigade.ledger.append_event import append_event
from brigade.ledger.signal_recorded import SignalRecorded
from brigade.runs.describe_finished import describe_finished
from brigade.runs.plan_run import RunPlan
from brigade.runs.run_locations import PROGRESS_FILE, RESULT_FILE
from brigade.runs.run_segment import TURN_LIMIT, WALL_LIMIT_OUTCOME, SegmentRecord, run_segment
from brigade.runtime import Runtime
from brigade.system.stop_signal_receiver import StopSignalReceiver
from brigade.system.write_json_atomically import write_json_atomically

BUDGET_REACHED = "budget_reached"
WALL_LIMIT_REACHED = "wall_limit_reached"
SOFT_LIMIT_OUTCOME = "soft_limit"
CLOCK_OUTCOMES = (WALL_LIMIT_OUTCOME, SOFT_LIMIT_OUTCOME)
BUDGET_EXCEEDED = "budget_exceeded"
RELAUNCH_SIGNALS = {
    TURN_LIMIT: BUDGET_REACHED,
    WALL_LIMIT_OUTCOME: WALL_LIMIT_REACHED,
    SOFT_LIMIT_OUTCOME: WALL_LIMIT_REACHED,
    "handed_over": "handed_over",
    "undeclared": "undeclared",
}


def _ends_on_the_clock(record: SegmentRecord) -> bool:
    return record.result.outcome in CLOCK_OUTCOMES


def _holds_progress(plan: RunPlan) -> bool:
    return bool((plan.run_directory / PROGRESS_FILE).read_text(encoding="utf-8").strip())


def _describe_signal(plan: RunPlan, record: SegmentRecord) -> SignalRecorded:
    ended_on_the_clock = _ends_on_the_clock(record)
    return SignalRecorded(
        signal=RELAUNCH_SIGNALS[record.result.outcome],
        project=plan.project,
        procedure=plan.procedure.name,
        run=plan.run_id,
        segment=record.number,
        budget=plan.procedure.budget,
        wall_limit_s=plan.wall_limit_s if ended_on_the_clock else None,
    )


def _describe_budget_exceeded(plan: RunPlan, record: SegmentRecord, steps: int) -> SignalRecorded:
    return SignalRecorded(
        signal=BUDGET_EXCEEDED,
        project=plan.project,
        procedure=plan.procedure.name,
        run=plan.run_id,
        segment=record.number,
        budget=plan.procedure.budget,
        steps=steps,
    )


def _run_with_handovers(plan: RunPlan, runtime: Runtime, stop: StopSignalReceiver) -> list[SegmentRecord]:
    records = []
    instant = runtime.now
    while True:
        record = run_segment(plan, len(records) + 1, runtime, stop)
        records.append(record)
        instant += timedelta(milliseconds=record.measured_ms)
        finished = describe_finished(plan, record)
        append_event(runtime.paths, instant, finished)
        if finished.main_steps is not None and finished.main_steps > plan.procedure.budget:
            append_event(runtime.paths, instant, _describe_budget_exceeded(plan, record, finished.main_steps))
        if record.result.outcome not in RELAUNCH_SIGNALS:
            return records
        append_event(runtime.paths, instant, _describe_signal(plan, record))
        if record.number > plan.handovers or not _holds_progress(plan):
            return records


def run_segments(plan: RunPlan, runtime: Runtime, stop: StopSignalReceiver) -> list[SegmentRecord]:
    if plan.disposable_worktree:
        add_detached_worktree(runtime.run_process, plan.cwd, plan.worktree)
    try:
        records = _run_with_handovers(plan, runtime, stop)
    finally:
        if plan.disposable_worktree:
            remove_worktree(runtime.run_process, plan.cwd, plan.worktree)
    write_json_atomically(plan.run_directory / RESULT_FILE, records[-1].result.to_document())
    return records
