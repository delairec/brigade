from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.commands._read_forge_environment import FORGE_KIND
from brigade.corpus.read_entities import Entity
from brigade.registry.read_project_forge import read_project_forge
from brigade.runtime import Runtime
from brigade.system.parse_configuration import Configuration

CLIENT_KIND = "client"


def equip_registered_collector(project: Entity, configuration: Configuration, runtime: Runtime) -> CollectorEquipment:
    forge_name = read_project_forge(project)
    return CollectorEquipment(
        configuration=configuration,
        forge=runtime.resolve_plugin(FORGE_KIND, forge_name),
        forge_name=forge_name,
        resolve_client=lambda name: runtime.resolve_plugin(CLIENT_KIND, name),
    )
