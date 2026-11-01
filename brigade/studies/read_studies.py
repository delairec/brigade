from brigade.corpus.read_entities import read_entities
from brigade.runtime import Runtime
from brigade.studies.convert_study import Study, convert_study
from brigade.studies.list_built_in_studies import list_built_in_studies

ENTITY_TYPE = "STUDY"


def read_studies(runtime: Runtime) -> tuple[Study, ...]:
    recorded = tuple(
        convert_study(entity) for entity in read_entities(runtime.run_process, runtime.paths.config_root, ENTITY_TYPE)
    )
    names = {study.name for study in recorded}
    return recorded + tuple(study for study in list_built_in_studies(runtime) if study.name not in names)
