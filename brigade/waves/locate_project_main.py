from collections.abc import Callable

from brigade.corpus.read_entities import Entity
from brigade.registry.read_project_field import read_project_field
from brigade.system.run_process import ProcessRecord, ProcessRequest
from brigade.waves.locate_forge_branch import locate_forge_branch


def locate_project_main(
    run_process: Callable[[ProcessRequest], ProcessRecord], project: Entity, read_environment: Callable[[str], dict]
) -> str:
    return locate_forge_branch(run_process, project, read_project_field(project, "MAIN"), read_environment)
