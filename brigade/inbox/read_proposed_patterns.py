from brigade.corpus.read_entities import Entity, read_entities
from brigade.registry.read_project_field import read_project_field
from brigade.runtime import Runtime
from brigade.triage.read_new_pattern import NEW_STATUS as PROPOSED_STATUS
from brigade.triage.read_new_pattern import PATTERN_TYPE


def read_proposed_patterns(runtime: Runtime) -> tuple[Entity, ...]:
    if not runtime.paths.schema_file.exists():
        return ()
    patterns = read_entities(runtime.run_process, runtime.paths.config_root, PATTERN_TYPE)
    return tuple(pattern for pattern in patterns if read_project_field(pattern, "STATUS") == PROPOSED_STATUS)
