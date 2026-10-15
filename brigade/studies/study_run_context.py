from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.runtime import Runtime
from brigade.studies.read_study import Study
from brigade.system.read_configuration import Configuration

STUDY_KIND = "study"
STEPS_DIRECTORY = "steps"
COLLECTORS_DIRECTORY = "collectors"
ANSWER_FILE = "answer.awawa"
STUDY_RECORD_FILE = "study.json"


@dataclass(frozen=True)
class StudyEquipment:
    configuration: Configuration
    resolve_collector: Callable[[str, Path], object]


@dataclass(frozen=True)
class StudyRunContext:
    runtime: Runtime
    study: Study
    run_id: str
    run_directory: Path
    equipment: StudyEquipment
