from brigade.corpus.read_entity import read_entity
from brigade.errors import BrigadeError, EntityNotDefined
from brigade.registry.require_operational_corpus import require_operational_corpus
from brigade.runtime import Runtime
from brigade.studies.convert_study import Study, convert_study
from brigade.studies.list_built_in_studies import list_built_in_studies
from brigade.studies.read_study_entity import ENTITY_TYPE


def read_study(runtime: Runtime, name: str) -> Study:
    require_operational_corpus(runtime.paths)
    try:
        return convert_study(read_entity(runtime.run_process, runtime.paths.config_root, ENTITY_TYPE, name))
    except EntityNotDefined:
        built_in = next((study for study in list_built_in_studies(runtime) if study.name == name), None)
    if built_in is None:
        raise BrigadeError(f"@{ENTITY_TYPE}.{name} is not defined in the operational corpus")
    return built_in
