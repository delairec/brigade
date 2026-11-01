from brigade.registry.read_projects import read_projects
from brigade.runtime import Runtime
from brigade.studies.convert_study import Study
from brigade.studies.describe_scans import describe_scans
from brigade.studies.describe_triage import describe_triage


def list_built_in_studies(runtime: Runtime) -> tuple[Study, ...]:
    return (describe_triage(), *(scan for project in read_projects(runtime) for scan in describe_scans(project.name)))
