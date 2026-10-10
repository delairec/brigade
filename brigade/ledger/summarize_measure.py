from brigade.ledger.finished_run import FinishedRun
from brigade.ledger.summarize_steps import summarize_steps


def _summarize_runs(runs: list[FinishedRun], measure: str) -> dict:
    measures = [getattr(run, measure) for run in runs]
    return {
        **summarize_steps(run_measure.value for run_measure in measures),
        "partial": sum(run_measure.partial for run_measure in measures),
    }


def summarize_measure(runs: list[FinishedRun], measure: str) -> dict:
    return {
        "runs": _summarize_runs(runs, measure),
        "segments": summarize_steps(getattr(segment, measure) for run in runs for segment in run.segments),
    }
