from brigade.corpus.read_entities import Entity, read_entities
from brigade.runtime import Runtime

ENTITY_TYPE = "PROJECT"


def read_projects(runtime: Runtime) -> tuple[Entity, ...]:
    return read_entities(runtime.run_process, runtime.paths.config_root, ENTITY_TYPE)
