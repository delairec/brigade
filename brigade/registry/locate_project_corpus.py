from pathlib import Path

from brigade.corpus.read_entities import Entity
from brigade.registry.read_corpus_workspace import MODE_FIELD, NONE_MODE, read_corpus_workspace
from brigade.registry.read_project_field import read_project_field


def locate_project_corpus(project: Entity | None) -> Path | None:
    if project is None or read_project_field(project, MODE_FIELD) == NONE_MODE:
        return None
    return read_corpus_workspace(project)
