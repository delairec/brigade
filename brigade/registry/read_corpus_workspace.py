from pathlib import Path

from brigade.corpus.read_entities import Entity
from brigade.errors import ToolFailure
from brigade.registry.read_project_field import read_project_field

MODE_FIELD = "MODE"
CORPUS_FIELD = "CORPUS"
AREA_MODE = "area"
NONE_MODE = "none"
WHOLE_REPOSITORY = Path()


def read_corpus_workspace(project: Entity) -> Path:
    mode = read_project_field(project, MODE_FIELD)
    if mode == NONE_MODE:
        raise ToolFailure(f"@PROJECT.{project.name} is in MODE none, which brigade does not deliver yet")
    if mode == AREA_MODE:
        return Path(read_project_field(project, CORPUS_FIELD))
    return WHOLE_REPOSITORY
