import dataclasses
from pathlib import Path

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.studies.study_run_context import StudyEquipment
from brigade.system.read_configuration import Configuration


def _refuse_collector(name: str, project: Path):
    raise AssertionError(f"the study resolved the collector {name}")


def _refuse_forge(name: str):
    raise AssertionError(f"the study resolved the forge {name}")


def _refuse_launch(request, runtime):
    raise AssertionError("the study launched a judging run")


def create_study_equipment(**changes) -> StudyEquipment:
    refusing_equipment = StudyEquipment(
        collector_equipment=CollectorEquipment(configuration=Configuration(), forge=None, forge_name="github"),
        resolve_collector=_refuse_collector,
        document=None,
        resolve_forge=_refuse_forge,
        launch_run=_refuse_launch,
    )
    return dataclasses.replace(refusing_equipment, **changes)
