import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.system.run_process import ProcessRecord, ProcessRequest

AWAWA_TIMEOUT_S = 30.0
QUOTE = '"'


@dataclass(frozen=True)
class EntityField:
    name: str
    value: str


@dataclass(frozen=True)
class Entity:
    name: str
    fields: tuple[EntityField, ...]


def _decode_atom(atom: str) -> str:
    if atom.startswith(QUOTE):
        return json.loads(atom)
    return atom


def read_entity(
    run_process: Callable[[ProcessRequest], ProcessRecord], root: Path, entity_type: str, name: str
) -> Entity:
    record = run_process(
        ProcessRequest(
            argv=("awawa", "show", f"@{entity_type}.{name}", "--json", str(root)),
            cwd=str(root),
            timeout_s=AWAWA_TIMEOUT_S,
        )
    )
    shown = json.loads(record.stdout)
    fields = tuple(
        EntityField(name=field["name"], value="".join(_decode_atom(atom) for atom in field["atoms"]))
        for field in shown["fields"]
    )
    return Entity(name=name, fields=fields)
