from datetime import UTC, date, datetime, time

from brigade.errors import BrigadeError
from brigade.ledger.read_ledger import LedgerReading
from brigade.ledger.run_finished import RunFinished
from brigade.ledger.summarize_steps import summarize_steps

REPORTED_MEASURES = ("steps_to_first_edit", "oversized_output_steps")


def _summarize_reported(runs: list[RunFinished], measure: str) -> dict | None:
    summary = summarize_steps(getattr(run, measure) for run in runs)
    if summary["measured"] == 0:
        return None
    return summary


def _describe_period(runs: list[RunFinished]) -> dict:
    return {
        "runs": len(runs),
        "steps": summarize_steps(run.main_steps for run in runs),
        **{measure: _summarize_reported(runs, measure) for measure in REPORTED_MEASURES},
    }


def describe_comparison(reading: LedgerReading, before: date) -> dict:
    boundary = datetime.combine(before, time(), tzinfo=UTC)
    runs = [entry for entry in reading.entries if isinstance(entry.event, RunFinished)]
    earlier_runs = [entry.event for entry in runs if entry.instant < boundary]
    later_runs = [entry.event for entry in runs if entry.instant >= boundary]
    if not earlier_runs:
        raise BrigadeError(f"no run finished before {before.isoformat()}")
    if not later_runs:
        raise BrigadeError(f"no run finished from {before.isoformat()} on")
    return {
        "before": before.isoformat(),
        "periods": {"before": _describe_period(earlier_runs), "from": _describe_period(later_runs)},
    }
