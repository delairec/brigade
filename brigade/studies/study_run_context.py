from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.runtime import Runtime
from brigade.studies.read_study import Study

STUDY_KIND = "study"
STEPS_DIRECTORY = "steps"
COLLECTORS_DIRECTORY = "collectors"
ANSWER_FILE = "answer.awawa"
STUDY_RECORD_FILE = "study.json"
CONTEXT_FILE = "context.json"
FIELDS_THE_CLI_FILLS = ("STUDY", "RUN", "COLLECTED")


@dataclass(frozen=True)
class StudyEquipment:
    collector_equipment: CollectorEquipment
    resolve_collector: Callable[[str, Path], object]
    document: object
    resolve_forge: Callable[[str], object]
    launch_run: Callable[[object, Runtime], dict]


@dataclass(frozen=True)
class StudyRunContext:
    runtime: Runtime
    study: Study
    run_id: str
    run_directory: Path
    equipment: StudyEquipment
