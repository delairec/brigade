from brigade.corpus.read_entities import Entity
from brigade.registry.is_on_github import is_on_github
from brigade.registry.read_project_field import read_project_field
from brigade.tick.actions import CollectCheckRuns

STATUS_FIELD = "STATUS"
PAUSED_STATUS = "paused"


def plan_connectors(projects: tuple[Entity, ...]) -> tuple[CollectCheckRuns, ...]:
    return tuple(
        CollectCheckRuns(project=project.name)
        for project in projects
        if read_project_field(project, STATUS_FIELD) != PAUSED_STATUS and is_on_github(project)
    )
