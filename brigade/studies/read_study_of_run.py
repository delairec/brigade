import json
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.runtime import Runtime
from brigade.studies.read_study import Study, read_study
from brigade.studies.study_run_context import STUDY_RECORD_FILE


def read_study_of_run(runtime: Runtime, run_directory: Path) -> Study:
    try:
        record = json.loads((run_directory / STUDY_RECORD_FILE).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise BrigadeError(f"{run_directory.name} is not a run of a study") from None
    return read_study(runtime, record["study"])
