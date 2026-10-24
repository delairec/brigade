from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.decode_atom import decode_atom
from brigade.corpus.read_entity import Entity, EntityField


@dataclass(frozen=True)
class PlanEntity:
    type: str
    entity: Entity


def _read_plan_entity(read_awawa_file_document, plan_file: Path, entity_type: str, name: str) -> PlanEntity:
    shown = read_awawa_file_document(plan_file, ("show", f"@{entity_type}.{name}"))
    fields = tuple(
        EntityField(name=field["name"], value="".join(map(decode_atom, field["atoms"]))) for field in shown["fields"]
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
