from dataclasses import asdict

from brigade.ledger.budget_applied import BudgetApplied
from brigade.ledger.current_digests import CurrentDigests
from brigade.ledger.describe_role_budget import describe_role_budget
from brigade.ledger.format_instant import format_instant
from brigade.ledger.is_measured_segment import is_measured_segment
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.read_ledger import LedgerReading
from brigade.ledger.run_finished import RunFinished
from brigade.ledger.select_current_segments import select_current_segments
from brigade.ledger.summarize_steps import summarize_steps

LATEST_RECORDED_DIGESTS = CurrentDigests(role=None, procedures={})


def _summarize_segment_turns(segments: tuple[RunFinished, ...]) -> dict:
    current = select_current_segments(segments, LATEST_RECORDED_DIGESTS)
    turns = summarize_steps(segment.main_turns for segment in current if is_measured_segment(segment))
    return {"segment_p50": turns["p50"], "segment_p90": turns["p90"]}


def _describe_change(entry: LedgerEntry) -> dict:
    change = entry.event
    return {
        "ts": format_instant(entry.instant),
        "before": change.before,
        "after": change.after,
        "direction": "raised" if change.after > change.before else "lowered",
    }


def _describe_role(segments: tuple[RunFinished, ...], shipped: int, changes: list[LedgerEntry]) -> dict:
    history = [_describe_change(entry) for entry in sorted(changes, key=lambda entry: entry.instant)]
    return {
        **asdict(describe_role_budget(segments, shipped, LATEST_RECORDED_DIGESTS)),
        **_summarize_segment_turns(segments),
        "history": history,
        "stable": not history,
    }


def describe_role_budgets(reading: LedgerReading) -> dict:
    segments = [entry.event for entry in reading.entries if isinstance(entry.event, RunFinished)]
    changes = [entry for entry in reading.entries if isinstance(entry.event, BudgetApplied)]
    shipped = {segment.role: segment.shipped_budget for segment in segments if segment.shipped_budget is not None}
    return {
        role: _describe_role(
            tuple(segment for segment in segments if segment.role == role),
            shipped[role],
            [entry for entry in changes if entry.event.role == role],
        )
        for role in sorted(shipped)
    }
