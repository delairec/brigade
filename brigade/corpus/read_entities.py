import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from brigade.system.run_process import ProcessRecord, ProcessRequest

AWAWA_TIMEOUT_S = 30.0
UNREADABLE_NAME = "?"
QUOTE = '"'


@dataclass(frozen=True)
class EntityField:
    name: str
    value: str


@dataclass(frozen=True)
class Entity:
    name: str
    fields: tuple[EntityField, ...]


def _read_json(run_process: Callable[[ProcessRequest], ProcessRecord], root: Path, arguments: tuple[str, ...]) -> dict:
    record = run_process(
        ProcessRequest(argv=("awawa", *arguments, "--json", str(root)), cwd=str(root), timeout_s=AWAWA_TIMEOUT_S)
    )
    return json.loads(record.stdout)


def _decode_atom(atom: str) -> str:
    if atom.startswith(QUOTE):
        return json.loads(atom)
    return atom


def _read_entity(
    run_process: Callable[[ProcessRequest], ProcessRecord], root: Path, entity_type: str, name: str
) -> Entity:
    shown = _read_json(run_process, root, ("show", f"@{entity_type}.{name}"))
    fields = tuple(
        EntityField(name=field["name"], value="".join(_decode_atom(atom) for atom in field["atoms"]))
        for field in shown["fields"]
    )
    return Entity(name=name, fields=fields)


def read_entities(
    run_process: Callable[[ProcessRequest], ProcessRecord], root: Path, entity_type: str
) -> tuple[Entity, ...]:
    status = _read_json(run_process, root, ("status", entity_type))
    names = sorted(
        entity["name"]
        for entity in status["entities"]
        if entity["type"] == entity_type and entity["name"] != UNREADABLE_NAME
    )
    return tuple(_read_entity(run_process, root, entity_type, name) for name in names)
