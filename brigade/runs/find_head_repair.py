from dataclasses import dataclass
from pathlib import Path

from brigade.runs.is_recorded_process_alive import is_recorded_process_alive
from brigade.runs.read_run_document import read_run_document
from brigade.runs.read_run_finished import read_run_finished
from brigade.runs.read_run_question import read_run_question
from brigade.runs.run_locations import RESULT_FILE, RUN_RECORD_FILE, RUNS_DIRECTORY
from brigade.runs.run_record import RUN_RECORD_SHAPE, RunRecord

REBASE_SLOT = "rebase"
BLOCKED_OUTCOME = "blocked"
DONE_OUTCOME = "done"


@dataclass(frozen=True)
class HeadRepair:
    run: str
    question: str | None


def _is_repair_of(record: RunRecord, branch: str, commit: str) -> bool:
    return record.slot == REBASE_SLOT and record.arguments == {**record.arguments, "branch": branch, "head": commit}


def _describe_repair(run_directory: Path, record: RunRecord) -> HeadRepair | None:
    result = run_directory / RESULT_FILE
    if not result.exists():
        return HeadRepair(run=record.run, question=None) if is_recorded_process_alive(run_directory) else None
    finished = read_run_finished(result, "run result")
    if finished.outcome == BLOCKED_OUTCOME:
        return HeadRepair(run=record.run, question=read_run_question(finished.message))
    if finished.outcome == DONE_OUTCOME:
        return HeadRepair(run=record.run, question=None)
    return None


def find_head_repair(state_root: Path, branch: str, commit: str) -> HeadRepair | None:
    for record_path in sorted((state_root / RUNS_DIRECTORY).glob(f"*/{RUN_RECORD_FILE}"), reverse=True):
        record = RunRecord.from_document(read_run_document(record_path, "run record", RUN_RECORD_SHAPE))
        if _is_repair_of(record, branch, commit):
            return _describe_repair(record_path.parent, record)
    return None
