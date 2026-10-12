import json
import re
from collections.abc import Callable
from pathlib import Path

from brigade.system.run_process import ProcessRecord, ProcessRequest

AWAWA_TIMEOUT_S = 30.0
SCHEMA_TYPE = "SCHEMA"
DECISION_TYPE = "DECISION"
TASK_TYPE = "TASK"
PLANNED_SCHEMAS = (TASK_TYPE, "WAVE")
ACTIVE_STATUS = "active"
OPEN_TASK_STATUSES = ("draft", "todo")
ANCHOR_FIELD = "IMPL"
ANCHOR_SEPARATOR = "::"
QUOTE = '"'
TRAILING_NUMBER = re.compile(r"\d+$")
SCHEMA_NOT_DEFINED = 1
SHOWN = (0,)
SHOWN_OR_NOT_DEFINED = (0, SCHEMA_NOT_DEFINED)


def _run_awawa(
    run_process: Callable[[ProcessRequest], ProcessRecord],
    root: Path,
    arguments: tuple[str, ...],
    acceptable_exit_codes: tuple[int, ...] = SHOWN,
) -> ProcessRecord:
    return run_process(
        ProcessRequest(
            argv=("awawa", *arguments, str(root)),
            cwd=str(root),
            timeout_s=AWAWA_TIMEOUT_S,
            acceptable_exit_codes=acceptable_exit_codes,
        )
    )


def _read_schema(run_process, root: Path, entity_type: str) -> str | None:
    record = _run_awawa(run_process, root, ("show", entity_type), SHOWN_OR_NOT_DEFINED)
    return None if record.exit_code == SCHEMA_NOT_DEFINED else record.stdout


def _decode_atom(atom: str) -> str:
    if atom.startswith(QUOTE):
        return json.loads(atom)
    return atom


def _read_value(fields: list, name: str) -> str:
    return next("".join(map(_decode_atom, field["atoms"])) for field in fields if field["name"] == name)


def _collect_anchors(fields: list) -> list[str]:
    return [
        anchor
        for field in fields
        for anchor in (
            [_decode_atom(field["atoms"][0])] if field["name"] == ANCHOR_FIELD else _collect_anchors(field["fields"])
        )
    ]


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
        for anchor in _collect_anchors(entity["fields"]):
            file = anchor.partition(ANCHOR_SEPARATOR)[0]
            anchors.setdefault(file, []).append({"entity": f"@{entity['type']}.{entity['name']}", "anchor": anchor})
    return anchors


def _count_next_task_number(entities: list) -> int:
    names = [entity["name"] for entity in entities if entity["type"] == TASK_TYPE]
    return max((int(digits) for name in names for digits in TRAILING_NUMBER.findall(name)), default=0) + 1


def assemble_plan_context(run_process: Callable[[ProcessRequest], ProcessRecord], root: Path) -> dict:
    status = json.loads(_run_awawa(run_process, root, ("status", "--json")).stdout)
    entities = [entity for entity in status["entities"] if entity["type"] != SCHEMA_TYPE]
    shown = [
        json.loads(_run_awawa(run_process, root, ("show", entity["target"], "--json")).stdout) for entity in entities
    ]
    schemas = {entity_type: _read_schema(run_process, root, entity_type) for entity_type in PLANNED_SCHEMAS}
    return {
        "status": _summarise_status(status["types"]),
        "decisions": [
            {"name": entity["name"], "title": _read_value(entity["fields"], "TITLE")}
            for entity in shown
            if entity["type"] == DECISION_TYPE and entity["status"] == ACTIVE_STATUS
        ],
        "tasks": [
            {"name": entity["name"], "status": entity["status"], "title": _read_value(entity["fields"], "TITLE")}
            for entity in shown
            if entity["type"] == TASK_TYPE and entity["status"] in OPEN_TASK_STATUSES
        ],
        "schemas": {entity_type: text for entity_type, text in schemas.items() if text is not None},
        "missing": [entity_type for entity_type, text in schemas.items() if text is None],
        "next_task_number": _count_next_task_number(entities),
        "anchors": _index_anchors(shown),
    }
