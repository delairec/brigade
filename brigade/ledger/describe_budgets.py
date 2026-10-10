from brigade.ledger.finished_run import FinishedRun
from brigade.ledger.group_runs import group_runs
from brigade.ledger.read_ledger import LedgerReading
from brigade.ledger.summarize_measure import summarize_measure

MEASURED_RUNS_FOR_A_MEASUREMENT = 5


def _summarize_procedure(runs: list[FinishedRun]) -> dict:
    steps = summarize_measure(runs, "main_steps")
    return {**steps, "estimate": steps["runs"]["measured"] < MEASURED_RUNS_FOR_A_MEASUREMENT}


def describe_budgets(reading: LedgerReading, last: int) -> dict:
    runs = group_runs(reading.entries)
    procedures = sorted({run.last.procedure for run in runs}, key=str)
    return {
        "last": last,
        "procedures": {
            procedure: _summarize_procedure([run for run in runs if run.last.procedure == procedure][-last:])
            for procedure in procedures
        },
    }
