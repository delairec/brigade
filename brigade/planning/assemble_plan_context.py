import json
from collections.abc import Callable
from pathlib import Path

from brigade.corpus.collect_anchors import collect_anchors
from brigade.errors import BrigadeError
from brigade.planning.count_next_task_number import count_next_task_number

SCHEMA_TYPE = "SCHEMA"
DECISION_TYPE = "DECISION"
TASK_TYPE = "TASK"
MILESTONE_TYPE = "MILESTONE"
PLANNED_SCHEMAS = (TASK_TYPE, MILESTONE_TYPE)
ACTIVE_STATUS = "active"
OPEN_TASK_STATUSES = ("draft", "todo")
TITLE_FIELD = "TITLE"
MILESTONE_FIELD = "MILESTONE"
FIELD_DECLARATION = "FIELD"
ANCHOR_SEPARATOR = "::"


def _read_declared_fields(read_awawa_document, root: Path, entity_type: str) -> list[str]:
    schema = read_awawa_document(root, ("show", entity_type))
    return [field["atoms"][0] for field in schema["fields"] if field["name"] == FIELD_DECLARATION]


def _list_missing(read_awawa_document, root: Path, schemas: dict) -> list[dict]:
    missing_types = [{"type": entity_type} for entity_type, text in schemas.items() if text is None]
    if schemas[TASK_TYPE] is None or MILESTONE_FIELD in _read_declared_fields(read_awawa_document, root, TASK_TYPE):
        return missing_types
    return [*missing_types, {"type": TASK_TYPE, "field": MILESTONE_FIELD}]


def _decode_atom(atom: str) -> str:
    return json.loads(atom)


def _read_title(entity: dict) -> str:
    titles = ["".join(map(_decode_atom, field["atoms"])) for field in entity["fields"] if field["name"] == TITLE_FIELD]
    if not titles:
        raise BrigadeError(f"@{entity['type']}.{entity['name']} holds no {TITLE_FIELD}")
    return titles[0]


def _summarise_status(types: list) -> list[dict]:
    return [
        {
            "type": row["type"],
            "total": row["total"],
            "counts": {status: count for status, count in row["counts"].items() if count},
        }
        for row in types
    ]


def _index_anchors(shown: list[dict]) -> dict:
    anchors = {}
    for entity in shown:
        for anchor in collect_anchors(entity["fields"]):
            file = anchor.partition(ANCHOR_SEPARATOR)[0]
            anchors.setdefault(file, []).append({"entity": f"@{entity['type']}.{entity['name']}", "anchor": anchor})
    return anchors


def assemble_plan_context(
    read_awawa_document: Callable[[Path, tuple[str, ...]], dict],
    read_schema: Callable[[Path, str], str | None],
    root: Path,
) -> dict:
    status = read_awawa_document(root, ("status",))
    entities = [entity for entity in status["entities"] if entity["type"] != SCHEMA_TYPE]
    shown = [read_awawa_document(root, ("show", entity["target"])) for entity in entities]
    schemas = {entity_type: read_schema(root, entity_type) for entity_type in PLANNED_SCHEMAS}
    return {
        "status": _summarise_status(status["types"]),
        "decisions": [
            {"name": entity["name"], "title": _read_title(entity)}
            for entity in shown
            if entity["type"] == DECISION_TYPE and entity["status"] == ACTIVE_STATUS
        ],
        "tasks": [
            {"name": entity["name"], "status": entity["status"], "title": _read_title(entity)}
            for entity in shown
            if entity["type"] == TASK_TYPE and entity["status"] in OPEN_TASK_STATUSES
        ],
        "schemas": {entity_type: text for entity_type, text in schemas.items() if text is not None},
        "missing": _list_missing(read_awawa_document, root, schemas),
        "next_task_number": count_next_task_number(entities),
        "anchors": _index_anchors(shown),
    }
