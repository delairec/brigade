from datetime import timedelta

from brigade.git.add_detached_worktree import add_detached_worktree
from brigade.git.remove_worktree import remove_worktree
from brigade.ledger.append_event import append_event
from brigade.ledger.signal_recorded import SignalRecorded
from brigade.runs.describe_finished import describe_finished
from brigade.runs.plan_run import RunPlan
from brigade.runs.run_locations import PROGRESS_FILE, RESULT_FILE
from brigade.runs.run_segment import WALL_LIMIT_OUTCOME, SegmentRecord, run_segment
from brigade.runtime import Runtime
from brigade.system.write_json_atomically import write_json_atomically

BUDGET_REACHED = "budget_reached"
WALL_LIMIT_REACHED = "wall_limit_reached"
TURN_LIMIT = "turn_limit"


def _is_cut_on_the_clock(record: SegmentRecord) -> bool:
    return record.result.outcome == WALL_LIMIT_OUTCOME


def _ends_on_budget(record: SegmentRecord) -> bool:
    return record.result.error_class == TURN_LIMIT or _is_cut_on_the_clock(record)


def _holds_progress(plan: RunPlan) -> bool:
    return bool((plan.run_directory / PROGRESS_FILE).read_text(encoding="utf-8").strip())


def _describe_signal(plan: RunPlan, record: SegmentRecord) -> SignalRecorded:
    cut_on_the_clock = _is_cut_on_the_clock(record)
    return SignalRecorded(
        signal=WALL_LIMIT_REACHED if cut_on_the_clock else BUDGET_REACHED,
        project=plan.project,
        procedure=plan.procedure.name,
        run=plan.run_id,
        segment=record.number,
        budget=plan.procedure.budget,
        wall_limit_s=plan.wall_limit_s if cut_on_the_clock else None,
    )


def _run_with_handovers(plan: RunPlan, runtime: Runtime) -> list[SegmentRecord]:
    records = []
    instant = runtime.now
    while True:
        record = run_segment(plan, len(records) + 1, runtime)
        records.append(record)
        instant += timedelta(milliseconds=record.measured_ms)
        append_event(runtime.paths, instant, describe_finished(plan, record))
        if not _ends_on_budget(record):
            return records
        append_event(runtime.paths, instant, _describe_signal(plan, record))
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
    write_json_atomically(plan.run_directory / RESULT_FILE, records[-1].result.to_document())
    return records
