import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.decode_atom import decode_atom
from brigade.corpus.run_awawa import run_awawa
from brigade.errors import CommandFailed, EntityNotDefined
from brigade.system.run_process import ProcessRecord, ProcessRequest

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


def read_entity(
    run_process: Callable[[ProcessRequest], ProcessRecord], root: Path, entity_type: str, name: str
) -> Entity:
    target = f"@{entity_type}.{name}"
    record = run_awawa(run_process, root, ("show", target, "--json", str(root)), SHOWN_OR_NOT)
    if record.exit_code == ENTITY_NOT_SHOWN:
        if UNKNOWN_ENTITY_DIAGNOSTIC in record.stderr:
            raise EntityNotDefined(f"{target} is not defined in {root}")
        raise CommandFailed(record.argv, record.exit_code, record.stderr)
    shown = json.loads(record.stdout)
    fields = tuple(
        EntityField(name=field["name"], value="".join(map(decode_atom, field["atoms"]))) for field in shown["fields"]
    )
    return Entity(name=name, fields=fields)
