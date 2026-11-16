from brigade.corpus.read_entities import read_entities
from brigade.orders.convert_order import convert_order
from brigade.runtime import Runtime
from brigade.studies.name_answer_file import name_answer_file
from brigade.studies.read_studies import read_studies

KINDS_BY_TYPE = {"REPORT": "wave-report", "ANSWER": "study-answer"}
REPORT_KINDS_BY_FIELD = {"MILESTONE": "milestone-report", "TASK": "task-report"}
ORDER_TYPE = "ORDER"
RESULT_TYPE = "RESULT"
UNRECORDED_ORDER = (None, None)


def _read_field(entity: dict, name: str) -> str | None:
    return next((field["value"] for field in entity["fields"] if field["name"] == name), None)


def _read_entities(runtime: Runtime, document: object, entity_type: str) -> list[dict]:
    path = runtime.paths.config_root / name_answer_file(entity_type)
    if not path.is_file():
        return []
    return document.render_document({"path": str(path)}, runtime)["entities"]


def _read_kind(entity: dict) -> str:
    return next(
        (kind for field, kind in REPORT_KINDS_BY_FIELD.items() if _read_field(entity, field) is not None),
        KINDS_BY_TYPE[entity["type"]],
    )


def _describe_report(entity: dict, kind: str | None, project: str | None) -> dict:
    return {
        "id": entity["name"],
        "kind": kind,
        "project": project,
        "type": entity["type"],
        "fields": entity["fields"],
    }


def read_reports(runtime: Runtime, document: object) -> list[dict]:
    projects_by_study = {study.name: study.project for study in read_studies(runtime)}
    wave_reports = [
        _describe_report(entity, _read_kind(entity), _read_field(entity, "PROJECT"))
        for entity in _read_entities(runtime, document, "REPORT")
    ]
    study_answers = [
        _describe_report(entity, _read_kind(entity), projects_by_study.get(_read_field(entity, "STUDY")))
        for entity in _read_entities(runtime, document, "ANSWER")
    ]
    kinds_and_projects_by_order = {
        order.name: (order.recipe, order.project)
        for order in map(convert_order, read_entities(runtime.run_process, runtime.paths.config_root, ORDER_TYPE))
    }
    order_results = [
        _describe_report(entity, *kinds_and_projects_by_order.get(_read_field(entity, ORDER_TYPE), UNRECORDED_ORDER))
        for entity in _read_entities(runtime, document, RESULT_TYPE)
    ]
    return wave_reports + study_answers + order_results
