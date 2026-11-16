from collections.abc import Callable

from brigade.runtime import Runtime
from brigade.studies.name_answer_file import name_answer_file
from brigade.studies.read_studies import read_studies

ANSWER_TYPE = "ANSWER"
STUDY_FIELD = "STUDY"


def _read_study(entity: dict) -> str | None:
    return next((field["value"] for field in entity["fields"] if field["name"] == STUDY_FIELD), None)


def read_study_answers(runtime: Runtime, resolve_document: Callable[[], object]) -> list[dict]:
    path = runtime.paths.config_root / name_answer_file(ANSWER_TYPE)
    if not path.is_file():
        return []
    document = resolve_document()
    projects_by_study = {study.name: study.project for study in read_studies(runtime)}
    return [
        {
            "id": entity["name"],
            "study": _read_study(entity),
            "project": projects_by_study.get(_read_study(entity)),
            "type": entity["type"],
            "fields": entity["fields"],
        }
        for entity in document.render_document({"path": str(path)}, runtime)["entities"]
    ]
