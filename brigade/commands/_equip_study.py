import functools
import os
from pathlib import Path

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.commands._read_forge_environment import FORGE_KIND
from brigade.commands._resolve_project_forge import resolve_project_forge
from brigade.commands.run_start import run
from brigade.corpus.read_entities import Entity
from brigade.registry.read_project_forge import read_project_forge
from brigade.runs.create_run_id import create_run_id
from brigade.runs.is_recorded_process_alive import is_recorded_process_alive
from brigade.runs.record_run_pid import record_run_pid
from brigade.runtime import Runtime
from brigade.studies.study_run_context import StudyEquipment
from brigade.system.collector_places import locate_collectors
from brigade.system.read_configuration import CONFIGURATION_OPTIONAL, read_configuration

CLIENT_KIND = "client"
COLLECTOR_KIND = "collector"
DOCUMENT_KIND = "progress_form"
ANSWER_DOCUMENT = "awawa"


def equip_study(project: Entity | None, runtime: Runtime) -> StudyEquipment:
    return StudyEquipment(
        collector_equipment=CollectorEquipment(
            configuration=read_configuration(runtime, CONFIGURATION_OPTIONAL),
            forge=resolve_project_forge(project, runtime),
            forge_name=read_project_forge(project),
            resolve_client=lambda name: runtime.resolve_plugin(CLIENT_KIND, name),
        ),
        resolve_collector=lambda name, project: runtime.resolve_plugin(
            COLLECTOR_KIND, name, places=locate_collectors(project, runtime.paths)
        ),
        document=runtime.resolve_plugin(DOCUMENT_KIND, ANSWER_DOCUMENT),
        resolve_forge=lambda name: runtime.resolve_plugin(FORGE_KIND, name),
        launch_run=run,
        name_run=create_run_id,
        working_directory=Path.cwd(),
        is_run_alive=is_recorded_process_alive,
        record_own_pid=functools.partial(record_run_pid, pid=os.getpid()),
    )
