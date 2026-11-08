from brigade.commands._read_forge_environment import FORGE_KIND
from brigade.corpus.read_entities import Entity
from brigade.registry.is_on_a_forge import is_on_a_forge
from brigade.registry.read_project_forge import read_project_forge
from brigade.runtime import Runtime

NO_FORGE_PLUGIN = None


def resolve_project_forge(project: Entity | None, runtime: Runtime) -> object:
    if not is_on_a_forge(project):
        return NO_FORGE_PLUGIN
    return runtime.resolve_plugin(FORGE_KIND, read_project_forge(project))
