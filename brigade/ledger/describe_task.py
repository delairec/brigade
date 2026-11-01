from brigade.errors import BrigadeError
from brigade.ledger.finished_run import FinishedRun
from brigade.ledger.format_instant import format_instant
from brigade.ledger.group_runs import group_runs
from brigade.ledger.read_ledger import LedgerReading
from brigade.ledger.run_finished import RunFinished
from brigade.ledger.sum_reported import sum_reported


def _present_run(run: FinishedRun) -> dict:
    steps = run.main_steps
    return {
        "run": run.run,
        "finished_at": format_instant(run.finished_at),
        "slot": run.last.slot,
        "outcome": run.last.outcome,
        "steps": steps.value,
        "partial": steps.partial,
        "duration_ms": sum_reported(segment.duration_ms for segment in run.segments),
        "cost_usd": sum_reported(segment.cost_usd for segment in run.segments),
    }


def describe_task(reading: LedgerReading, task: str) -> dict:
    runs = group_runs(
        entry for entry in reading.entries if isinstance(entry.event, RunFinished) and entry.event.task == task
    )
    if not runs:
        raise BrigadeError(f"no run names the task {task}")
    return {"view": "task", "task": task, "runs": [_present_run(run) for run in runs]}
