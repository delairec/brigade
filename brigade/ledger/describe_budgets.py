from brigade.ledger.read_ledger import LedgerReading
from brigade.ledger.run_finished import RunFinished
from brigade.ledger.summarize_steps import summarize_steps

MEASURED_RUNS_FOR_A_MEASUREMENT = 5


def _summarize_procedure(runs: list[RunFinished]) -> dict:
    summary = summarize_steps(run.main_steps for run in runs)
    return {**summary, "estimate": summary["measured"] < MEASURED_RUNS_FOR_A_MEASUREMENT}


def describe_budgets(reading: LedgerReading, last: int) -> dict:
    runs = [entry.event for entry in reading.entries if isinstance(entry.event, RunFinished)]
    procedures = sorted({run.procedure for run in runs}, key=str)
    return {
        "last": last,
        "procedures": {
            procedure: _summarize_procedure([run for run in runs if run.procedure == procedure][-last:])
            for procedure in procedures
        },
    }
