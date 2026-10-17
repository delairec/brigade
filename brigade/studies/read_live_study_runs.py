import json
from dataclasses import dataclass
from pathlib import Path

from brigade.runs.is_recorded_process_alive import is_recorded_process_alive
from brigade.runs.run_locations import RUNS_DIRECTORY
from brigade.studies.study_run_context import STUDY_RECORD_FILE


@dataclass(frozen=True)
class LiveStudyRun:
    study: str
    run: str

    def to_document(self) -> dict:
        return {"study": self.study, "run": self.run}


def read_live_study_runs(state_root: Path) -> tuple[LiveStudyRun, ...]:
    return tuple(
        LiveStudyRun(study=json.loads(record.read_text(encoding="utf-8"))["study"], run=record.parent.name)
        for record in sorted((state_root / RUNS_DIRECTORY).glob(f"*/{STUDY_RECORD_FILE}"))
        if is_recorded_process_alive(record.parent)
    )
