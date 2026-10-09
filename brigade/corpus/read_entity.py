import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.errors import CommandFailed, EntityNotDefined
from brigade.system.run_process import ProcessRecord, ProcessRequest

AWAWA_TIMEOUT_S = 30.0
QUOTE = '"'
ENTITY_NOT_SHOWN = 1
SHOWN_OR_NOT = (0, ENTITY_NOT_SHOWN)
UNKNOWN_ENTITY_DIAGNOSTIC = "is not defined in the workspace"


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
    target = f"@{entity_type}.{name}"
    argv = ("awawa", "show", target, "--json", str(root))
    record = run_process(
        ProcessRequest(argv=argv, cwd=str(root), timeout_s=AWAWA_TIMEOUT_S, acceptable_exit_codes=SHOWN_OR_NOT)
    )
    if record.exit_code == ENTITY_NOT_SHOWN:
        if UNKNOWN_ENTITY_DIAGNOSTIC in record.stderr:
            raise EntityNotDefined(f"{target} is not defined in {root}")
        raise CommandFailed(record.argv, record.exit_code, record.stderr)
    shown = json.loads(record.stdout)
    fields = tuple(
        EntityField(name=field["name"], value="".join(_decode_atom(atom) for atom in field["atoms"]))
        for field in shown["fields"]
    )
    return Entity(name=name, fields=fields)
