from collections.abc import Callable
from pathlib import Path

from brigade.corpus.read_entities import Entity
from brigade.corpus.read_entity import read_entity
from brigade.errors import EntityNotDefined
from brigade.registry.locate_project_corpus import locate_project_corpus
from brigade.registry.read_project_field import read_project_field
from brigade.reports.read_reports import REPORT_KINDS_BY_FIELD
from brigade.system.run_process import ProcessRecord, ProcessRequest

MILESTONE_FIELD = "MILESTONE"
NO_TITLE = None


def read_milestone_title(
    run_process: Callable[[ProcessRequest], ProcessRecord], projects: tuple[Entity, ...], report: dict
) -> str | None:
    if report["kind"] != REPORT_KINDS_BY_FIELD[MILESTONE_FIELD]:
        return NO_TITLE
    project = next((project for project in projects if project.name == report["project"]), None)
    corpus = locate_project_corpus(project)
    if corpus is None:
        return NO_TITLE
    milestone = next(field["value"] for field in report["fields"] if field["name"] == MILESTONE_FIELD)
    root = Path(read_project_field(project, "PATH")) / corpus
    try:
        return read_project_field(read_entity(run_process, root, MILESTONE_FIELD, milestone), "TITLE")
    except EntityNotDefined:
        return NO_TITLE
