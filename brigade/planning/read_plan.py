import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.read_entity import Entity, EntityField

QUOTE = '"'


@dataclass(frozen=True)
class PlanEntity:
    type: str
    entity: Entity


def _decode_atom(atom: str) -> str:
    if atom.startswith(QUOTE):
        return json.loads(atom)
    return atom


def _read_plan_entity(read_awawa_file_document, plan_file: Path, entity_type: str, name: str) -> PlanEntity:
    shown = read_awawa_file_document(plan_file, ("show", f"@{entity_type}.{name}"))
    fields = tuple(
        EntityField(name=field["name"], value="".join(_decode_atom(atom) for atom in field["atoms"]))
        for field in shown["fields"]
    )
    return PlanEntity(type=entity_type, entity=Entity(name=name, fields=fields))


def read_plan(
    read_awawa_file_document: Callable[[Path, tuple[str, ...]], dict], plan_file: Path
) -> tuple[PlanEntity, ...]:
    listed = read_awawa_file_document(plan_file, ("show", str(plan_file)))
    return tuple(
        _read_plan_entity(read_awawa_file_document, plan_file, entity["type"], entity["name"])
        for entity in listed["entities"]
    )
