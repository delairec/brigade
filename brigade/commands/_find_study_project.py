from pathlib import Path

from brigade.corpus.read_entities import Entity
from brigade.registry.find_project import find_project
from brigade.registry.find_project_at import find_project_at
from brigade.registry.read_projects import read_projects
from brigade.runtime import Runtime
from brigade.studies.read_study import Study


def find_study_project(study: Study, runtime: Runtime) -> Entity | None:
    projects = read_projects(runtime)
    if study.project is None:
        return find_project_at(projects, Path.cwd())
    return find_project(projects, study.project)
