from brigade.corpus.read_entity import Entity, read_entity
from brigade.errors import BrigadeError, EntityNotDefined
from brigade.registry.read_project_field import read_project_field
from brigade.registry.require_operational_corpus import require_operational_corpus
from brigade.runtime import Runtime

PATTERN_TYPE = "PATTERN"
NEW_STATUS = "new"


def read_new_pattern(runtime: Runtime, name: str) -> Entity:
    require_operational_corpus(runtime.paths)
    try:
        pattern = read_entity(runtime.run_process, runtime.paths.config_root, PATTERN_TYPE, name)
    except EntityNotDefined:
        raise BrigadeError(f"@{PATTERN_TYPE}.{name} is not defined in the operational corpus") from None
    status = read_project_field(pattern, "STATUS")
    if status != NEW_STATUS:
        raise BrigadeError(f"@{PATTERN_TYPE}.{name} is {status}: only a {NEW_STATUS} pattern is ratified or dismissed")
    return pattern
