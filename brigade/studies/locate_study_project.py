from dataclasses import dataclass
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.registry.describe_remote import NO_FORGE
from brigade.registry.find_project import find_project
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_projects import read_projects
from brigade.studies.study_run_context import StudyRunContext


@dataclass(frozen=True)
class StudyProject:
    path: Path
    forge: str | None


def locate_study_project(context: StudyRunContext) -> StudyProject:
    if context.study.project is None:
        raise BrigadeError(f"the output {context.study.output} needs a project")
    project = find_project(read_projects(context.runtime), context.study.project)
    forge = read_project_field(project, "FORGE")
    return StudyProject(path=Path(read_project_field(project, "PATH")), forge=None if forge == NO_FORGE else forge)
