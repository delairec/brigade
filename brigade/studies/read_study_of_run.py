import json
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.wave_started import WaveStarted
from brigade.runtime import Runtime
from brigade.studies.describe_wave_report import describe_wave_report
from brigade.studies.read_study import Study, read_study
from brigade.studies.study_run_context import STUDY_RECORD_FILE
from brigade.waves.find_wave_started import find_wave_started

WAVE_KEY = "wave"


def _read_wave_started(runtime: Runtime, wave: str) -> WaveStarted:
    return find_wave_started(tuple(entry.event for entry in read_ledger(runtime.paths.state_root).entries), wave)


def read_study_of_run(runtime: Runtime, run_directory: Path) -> Study:
    try:
        record = json.loads((run_directory / STUDY_RECORD_FILE).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise BrigadeError(f"{run_directory.name} is not a run of a study") from None
    if record.get(WAVE_KEY) is not None:
        return describe_wave_report(_read_wave_started(runtime, record[WAVE_KEY]))
    return read_study(runtime, record["study"])
