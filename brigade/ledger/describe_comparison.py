from datetime import UTC, date, datetime, time

from brigade.errors import BrigadeError
from brigade.ledger.finished_run import FinishedRun
from brigade.ledger.group_runs import group_runs
from brigade.ledger.read_ledger import LedgerReading
from brigade.ledger.summarize_measure import summarize_measure

REPORTED_MEASURES = ("steps_to_first_edit", "oversized_output_steps")


def _summarize_reported(runs: list[FinishedRun], measure: str) -> dict | None:
    summary = summarize_measure(runs, measure)
    if summary["segments"]["measured"] == 0:
        return None
    return summary


def _describe_period(runs: list[FinishedRun]) -> dict:
    return {
        "runs": len(runs),
        "segments": sum(len(run.segments) for run in runs),
        "steps": summarize_measure(runs, "main_steps"),
        **{measure: _summarize_reported(runs, measure) for measure in REPORTED_MEASURES},
    }


def describe_comparison(reading: LedgerReading, before: date) -> dict:
    boundary = datetime.combine(before, time(), tzinfo=UTC)
    runs = group_runs(reading.entries)
    earlier_runs = [run for run in runs if run.finished_at < boundary]
    later_runs = [run for run in runs if run.finished_at >= boundary]
    if not earlier_runs:
        raise BrigadeError(f"no run finished before {before.isoformat()}")
    if not later_runs:
        raise BrigadeError(f"no run finished from {before.isoformat()} on")
    return {
        "before": before.isoformat(),
        "periods": {"before": _describe_period(earlier_runs), "from": _describe_period(later_runs)},
    }
