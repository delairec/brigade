from datetime import datetime
from pathlib import Path

from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.order_parked import OrderParked
from brigade.ledger.run_finished import RunFinished
from brigade.runs.read_run_document import read_run_document
from brigade.runs.run_locations import RUN_RECORD_FILE, RUNS_DIRECTORY
from brigade.runs.run_record import RUN_RECORD_SHAPE, RunRecord
from brigade.studies.study_run_context import STUDY_KIND
from brigade.tick.decide_resume_at import decide_resume_at

RATE_LIMIT = "rate_limit"
ORDER_ARGUMENT = "run"


def _read_order_run(state_root: Path, judging_run: str) -> str | None:
    record_path = state_root / RUNS_DIRECTORY / judging_run / RUN_RECORD_FILE
    if not record_path.is_file():
        return None
    record = RunRecord.from_document(read_run_document(record_path, "run record", RUN_RECORD_SHAPE))
    return record.arguments.get(ORDER_ARGUMENT)


def read_quota_resumes(state_root: Path, entries: tuple[LedgerEntry, ...]) -> dict[str, datetime]:
    cuts: dict[str, datetime] = {}
    resumes: dict[str, datetime] = {}
    for entry in entries:
        event = entry.event
        if isinstance(event, RunFinished) and event.error_class == RATE_LIMIT:
            order_run = _read_order_run(state_root, event.run)
            if order_run is not None:
                cuts[order_run] = decide_resume_at(entry.instant, event.reset)
        elif isinstance(event, OrderParked) and event.kind == STUDY_KIND:
            resumes.pop(event.run, None)
            if event.run in cuts:
                resumes[event.run] = cuts.pop(event.run)
    return resumes
