from brigade.corpus.read_entity import read_entity
from brigade.errors import EntityNotDefined
from brigade.registry.require_operational_corpus import require_operational_corpus
from brigade.runtime import Runtime
from brigade.studies.convert_study import Study, convert_study
from brigade.studies.describe_triage import NAME as TRIAGE
from brigade.studies.describe_triage import describe_triage
from brigade.studies.read_study_entity import ENTITY_TYPE, read_study_entity

BUILT_IN_STUDIES = {TRIAGE: describe_triage}


def read_study(runtime: Runtime, name: str) -> Study:
    describe_built_in = BUILT_IN_STUDIES.get(name)
    if describe_built_in is None:
        return convert_study(read_study_entity(runtime, name))
    require_operational_corpus(runtime.paths)
    try:
        return convert_study(read_entity(runtime.run_process, runtime.paths.config_root, ENTITY_TYPE, name))
    except EntityNotDefined:
        return describe_built_in()
