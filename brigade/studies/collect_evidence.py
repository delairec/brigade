import dataclasses
from datetime import date
from pathlib import Path

from brigade.collecting.collect_document import CollectionRequest, collect_document
from brigade.collecting.collector_environment import CollectorInputs
from brigade.registry.find_project import find_project
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_projects import read_projects
from brigade.studies.read_collector_line import read_collector_line
from brigade.studies.study_run_context import COLLECTORS_DIRECTORY, StudyRunContext

BEGINNING = date(1970, 1, 1)
FIRST_COLLECTOR = 1


def _locate_project(context: StudyRunContext) -> Path:
    if context.study.project is None:
        return Path.cwd()
    project = find_project(read_projects(context.runtime), context.study.project)
    return Path(read_project_field(project, "PATH"))


def collect_evidence(context: StudyRunContext) -> dict:
    runtime = context.runtime
    project = _locate_project(context)
    collected = []
    declared_collectors = [read_collector_line(line) for line in context.study.collectors]
    for index, (name, parameters) in enumerate(declared_collectors, start=FIRST_COLLECTOR):
        collector = context.equipment.resolve_collector(name, project)
        place = context.run_directory / COLLECTORS_DIRECTORY / str(index)
        collection = collect_document(
            collector,
            CollectionRequest(
                inputs=CollectorInputs(project=project, since=BEGINNING, parameters=parameters),
                refresh=False,
                configuration=context.equipment.configuration,
            ),
            dataclasses.replace(runtime, paths=dataclasses.replace(runtime.paths, run_directory=place)),
        )
        collected.append(
            {
                "collector": collector.name,
                "summary": collection.document["summary"],
                "document": str(collection.document_path),
            }
        )
    return {"collected": collected}
