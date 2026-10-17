from brigade.corpus.read_entity import read_entity
from brigade.errors import BrigadeError, EntityNotDefined
from brigade.registry.require_operational_corpus import require_operational_corpus
from brigade.runtime import Runtime
from brigade.studies.convert_study import Study, convert_study

ENTITY_TYPE = "STUDY"


def read_study(runtime: Runtime, name: str) -> Study:
    require_operational_corpus(runtime.paths)
    try:
        entity = read_entity(runtime.run_process, runtime.paths.config_root, ENTITY_TYPE, name)
    except EntityNotDefined:
        raise BrigadeError(f"@{ENTITY_TYPE}.{name} is not defined in the operational corpus") from None
    return convert_study(entity)
