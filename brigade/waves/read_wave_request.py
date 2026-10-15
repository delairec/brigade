from brigade.corpus.read_entity import Entity, read_entity
from brigade.errors import BrigadeError, EntityNotDefined
from brigade.registry.require_operational_corpus import require_operational_corpus
from brigade.runtime import Runtime

ENTITY_TYPE = "REQUEST"


def read_wave_request(runtime: Runtime, name: str) -> Entity:
    require_operational_corpus(runtime.paths)
    try:
        return read_entity(runtime.run_process, runtime.paths.config_root, ENTITY_TYPE, name)
    except EntityNotDefined:
        raise BrigadeError(f"@{ENTITY_TYPE}.{name} is not defined in the operational corpus") from None
