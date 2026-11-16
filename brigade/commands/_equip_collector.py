from pathlib import Path

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.commands._resolve_project_forge import resolve_project_forge
from brigade.registry.find_project_at import find_project_at
from brigade.registry.read_project_forge import read_project_forge
from brigade.registry.read_projects import read_projects
from brigade.runtime import Runtime
from brigade.system.read_configuration import CONFIGURATION_OPTIONAL, read_configuration

CLIENT_KIND = "client"


def equip_collector(project: Path, runtime: Runtime) -> CollectorEquipment:
    registered = find_project_at(read_projects(runtime), project)
    return CollectorEquipment(
        configuration=read_configuration(runtime, CONFIGURATION_OPTIONAL),
        forge=resolve_project_forge(registered, runtime),
        forge_name=read_project_forge(registered),
        resolve_client=lambda name: runtime.resolve_plugin(CLIENT_KIND, name),
    )
