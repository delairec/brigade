from datetime import UTC, datetime, time, timedelta

from brigade.errors import BrigadeError
from brigade.ledger.finished_run import FinishedRun
from brigade.ledger.group_runs import group_runs
from brigade.ledger.read_ledger import LedgerReading
from brigade.ledger.summarize_measure import summarize_measure
from brigade.system.read_day_range import DayRange

REPORTED_MEASURES = ("steps_to_first_edit", "oversized_output_steps")
PER_LAUNCH_DECIMALS = 2
FOLLOWING_DAY = timedelta(days=1)


def _summarize_reported(runs: list[FinishedRun], measure: str) -> dict | None:
    summary = summarize_measure(runs, measure)
    if summary["segments"]["measured"] == 0:
        return None
    return summary


def _average_per_launch(runs: list[FinishedRun]) -> float | None:
    reported = [
        segment.oversized_output_steps
        for run in runs
        for segment in run.segments
        if segment.oversized_output_steps is not None
    ]
    if not reported:
        return None
    return round(sum(reported) / len(reported), PER_LAUNCH_DECIMALS)


def _measure_figures(runs: list[FinishedRun]) -> dict:
    task_runs = [run for run in runs if run.last.task is not None]
    return {
        "steps_to_first_edit_p50": summarize_measure(runs, "steps_to_first_edit")["runs"]["p50"],
        "task_run_steps_p50": summarize_measure(task_runs, "main_steps")["runs"]["p50"],
        "oversized_output_steps_per_launch": _average_per_launch(runs),
    }


def _select_range(runs: list[FinishedRun], day_range: DayRange) -> list[FinishedRun]:
    start = datetime.combine(day_range.start, time(), tzinfo=UTC)
    end = datetime.combine(day_range.end + FOLLOWING_DAY, time(), tzinfo=UTC)
    selected = [run for run in runs if start <= run.finished_at < end]
    if not selected:
        raise BrigadeError(f"no run finished from {day_range.start.isoformat()} to {day_range.end.isoformat()}")
    return selected


def _describe_range(runs: list[FinishedRun], day_range: DayRange) -> dict:
    selected = _select_range(runs, day_range)
    return {
        "start": day_range.start.isoformat(),
        "end": day_range.end.isoformat(),
        "runs": len(selected),
        "segments": sum(len(run.segments) for run in selected),
        "steps": summarize_measure(selected, "main_steps"),
        **{measure: _summarize_reported(selected, measure) for measure in REPORTED_MEASURES},
        "figures": _measure_figures(selected),
    }


def describe_comparison(reading: LedgerReading, ranges: tuple[DayRange, ...], reference: dict) -> dict:
    runs = group_runs(reading.entries)
    return {"ranges": [_describe_range(runs, day_range) for day_range in ranges], "reference": reference}
