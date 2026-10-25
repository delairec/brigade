from brigade.corpus.read_entities import read_entities
from brigade.runtime import Runtime
from brigade.studies.convert_study import Study, convert_study
from brigade.studies.read_study import BUILT_IN_STUDIES

ENTITY_TYPE = "STUDY"


def read_studies(runtime: Runtime) -> tuple[Study, ...]:
    recorded = tuple(
        convert_study(entity) for entity in read_entities(runtime.run_process, runtime.paths.config_root, ENTITY_TYPE)
    )
    names = {study.name for study in recorded}
    return recorded + tuple(describe() for name, describe in BUILT_IN_STUDIES.items() if name not in names)
