import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.orders.start_order_run import ORDER_RECORD_FILE
from brigade.runs.run_locations import RUNS_DIRECTORY
from brigade.studies.study_run_context import STUDY_KIND


@dataclass(frozen=True)
class LiveStudyRun:
    study: str
    run: str

    def to_document(self) -> dict:
        return {"study": self.study, "run": self.run}


def _read_record(record: Path) -> dict:
    return json.loads(record.read_text(encoding="utf-8"))


def read_live_study_runs(state_root: Path, is_alive: Callable[[Path], bool]) -> tuple[LiveStudyRun, ...]:
    return tuple(
        LiveStudyRun(study=_read_record(record)["order"]["name"], run=record.parent.name)
        for record in sorted((state_root / RUNS_DIRECTORY).glob(f"*/{ORDER_RECORD_FILE}"))
        if is_alive(record.parent) and _read_record(record)["recipe"]["name"] == STUDY_KIND
    )
