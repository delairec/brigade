from brigade.runtime import Runtime
from brigade.studies.name_answer_file import name_answer_file
from brigade.studies.read_studies import read_studies

KINDS_BY_TYPE = {"REPORT": "wave-report", "ANSWER": "study-answer"}


def _read_field(entity: dict, name: str) -> str | None:
    return next((field["value"] for field in entity["fields"] if field["name"] == name), None)


def _read_entities(runtime: Runtime, document: object, entity_type: str) -> list[dict]:
    path = runtime.paths.config_root / name_answer_file(entity_type)
    if not path.is_file():
        return []
    return document.render_document({"path": str(path)}, runtime)["entities"]


def _describe_report(entity: dict, project: str | None) -> dict:
    return {
        "id": entity["name"],
        "kind": KINDS_BY_TYPE[entity["type"]],
        "project": project,
        "type": entity["type"],
        "fields": entity["fields"],
    }


def read_reports(runtime: Runtime, document: object) -> list[dict]:
    projects_by_study = {study.name: study.project for study in read_studies(runtime)}
    wave_reports = [
        _describe_report(entity, _read_field(entity, "PROJECT"))
        for entity in _read_entities(runtime, document, "REPORT")
    ]
    study_answers = [
        _describe_report(entity, projects_by_study.get(_read_field(entity, "STUDY")))
        for entity in _read_entities(runtime, document, "ANSWER")
    ]
    return wave_reports + study_answers
