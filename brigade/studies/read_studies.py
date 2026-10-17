from brigade.corpus.read_entities import read_entities
from brigade.runtime import Runtime
from brigade.studies.convert_study import Study, convert_study

ENTITY_TYPE = "STUDY"


def read_studies(runtime: Runtime) -> tuple[Study, ...]:
    return tuple(
        convert_study(entity) for entity in read_entities(runtime.run_process, runtime.paths.config_root, ENTITY_TYPE)
    )
