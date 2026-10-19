import dataclasses
from datetime import datetime
from pathlib import Path

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.studies.study_run_context import StudyEquipment
from brigade.system.read_configuration import Configuration

UNUSED_WORKING_DIRECTORY = Path("/the/study/reads/no/working/directory")


def _refuse_collector(name: str, project: Path):
    raise AssertionError(f"the study resolved the collector {name}")


def _refuse_forge(name: str):
    raise AssertionError(f"the study resolved the forge {name}")


def _refuse_launch(request, runtime):
    raise AssertionError("the study launched a judging run")


def _refuse_naming(now: datetime) -> str:
    raise AssertionError("the study named a new run")


def _refuse_probe(run_directory: Path) -> bool:
    raise AssertionError(f"the study probed the process of the run {run_directory.name}")


def _refuse_holding(run_directory: Path) -> None:
    raise AssertionError(f"the study held the run {run_directory.name}")


def create_study_equipment(**changes) -> StudyEquipment:
    refusing_equipment = StudyEquipment(
        collector_equipment=CollectorEquipment(configuration=Configuration(), forge=None, forge_name="github"),
        resolve_collector=_refuse_collector,
        document=None,
        resolve_forge=_refuse_forge,
        launch_run=_refuse_launch,
        name_run=_refuse_naming,
        working_directory=UNUSED_WORKING_DIRECTORY,
        is_run_alive=_refuse_probe,
        record_own_pid=_refuse_holding,
    )
    return dataclasses.replace(refusing_equipment, **changes)
