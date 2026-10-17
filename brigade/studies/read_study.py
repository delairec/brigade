from brigade.runtime import Runtime
from brigade.studies.convert_study import Study, convert_study
from brigade.studies.read_study_entity import read_study_entity


def read_study(runtime: Runtime, name: str) -> Study:
    return convert_study(read_study_entity(runtime, name))
