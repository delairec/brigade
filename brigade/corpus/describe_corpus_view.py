from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.read_awawa_document import read_awawa_document
from brigade.corpus.read_entity import read_entity
from brigade.system.run_process import ProcessRecord, ProcessRequest

UNREADABLE_NAME = "?"
DEPENDENCY_DEPTH = 1


@dataclass(frozen=True)
class CorpusView:
    entity_type: str
    field: str | None = None
    entity: str | None = None
    ide_link: str = ""


def _name_target(entity: dict) -> str:
    return f"@{entity['type']}.{entity['name']}"


def _link_line(ide_link: str, file: str, line: int) -> str | None:
    if not ide_link:
        return None
    return ide_link.replace("{path}", file).replace("{line}", str(line))


def _describe_entity(entity: dict, root: Path, ide_link: str) -> dict:
    return {
        "target": _name_target(entity),
        "status": entity["status"],
        "file": str(Path(entity["file"]).relative_to(root)),
        "line": entity["line"],
        "ide_link": _link_line(ide_link, entity["file"], entity["line"]),
    }


def _describe_board(
    run_process: Callable[[ProcessRequest], ProcessRecord], root: Path, listed: list[dict], field: str
) -> list[dict]:
    columns: dict[str | None, list[str]] = {}
    for entity in listed:
        fields = read_entity(run_process, root, entity["type"], entity["name"]).fields
        for value in [read.value for read in fields if read.name == field] or [None]:
            columns.setdefault(value, []).append(_name_target(entity))
    ordered = sorted(columns, key=lambda value: (value is None, value or ""))
    return [{"value": value, "targets": columns[value]} for value in ordered]


def _describe_dependencies(
    run_process: Callable[[ProcessRequest], ProcessRecord], root: Path, view: CorpusView
) -> dict:
    context = read_awawa_document(run_process, root, ("context", view.entity, "--depth", str(DEPENDENCY_DEPTH)))
    referencing = [
        _name_target(reference) for reference in context["referenced_by"] if reference["target"] == view.entity
    ]
    return {
        "entity": view.entity,
        "reaches": [
            _describe_entity(entity, root, view.ide_link) for entity in context["entities"] if entity["depth"] > 0
        ],
        "referenced_by": list(dict.fromkeys(referencing)),
    }


def describe_corpus_view(run_process: Callable[[ProcessRequest], ProcessRecord], root: Path, view: CorpusView) -> dict:
    status = read_awawa_document(run_process, root, ("status", view.entity_type))
    listed = sorted(
        (
            entity
            for entity in status["entities"]
            if entity["type"] == view.entity_type and entity["name"] != UNREADABLE_NAME
        ),
        key=lambda entity: (entity["file"], entity["line"]),
    )
    document = {
        "type": view.entity_type,
        "types": [row["type"] for row in status["types"]],
        "entities": [_describe_entity(entity, root, view.ide_link) for entity in listed],
    }
    if view.field is not None:
        document |= {"field": view.field, "board": _describe_board(run_process, root, listed, view.field)}
    if view.entity is not None:
        document["dependencies"] = _describe_dependencies(run_process, root, view)
    return document
