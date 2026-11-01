import json
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.inbox.record_signal import NewSignal, record_signal
from brigade.studies.read_collected import read_collected
from brigade.studies.study_run_context import StudyRunContext

SCAN_KIND = "scan"
FINGERPRINT_KEY = "fingerprint"
NO_PROJECT_NAME = ""


def _read_items(entry: dict) -> list[dict]:
    items = json.loads(Path(entry["document"]).read_text(encoding="utf-8"))["items"]
    if any(FINGERPRINT_KEY not in item for item in items):
        raise BrigadeError(f"the collector {entry['collector']} printed an item without a fingerprint")
    return items


def record_scan_signals(context: StudyRunContext) -> dict:
    study = context.study
    items = [item for entry in read_collected(context.run_directory) for item in _read_items(entry)]
    project_name = study.project or NO_PROJECT_NAME
    for item in items:
        record_signal(
            context.runtime.paths,
            context.runtime.now,
            NewSignal(
                kind=SCAN_KIND,
                project=study.project,
                fingerprint=f"{study.name}:{project_name}:{item[FINGERPRINT_KEY]}",
                evidence=item,
            ),
        )
    return {"signals": len(items)}
