import json
from collections.abc import Callable
from pathlib import Path

from brigade.corpus.decode_entity import decode_entity
from brigade.corpus.entity import Entity, EntityField
from brigade.corpus.run_awawa import run_awawa
from brigade.errors import CommandFailed, EntityNotDefined
from brigade.system.run_process import ProcessRecord, ProcessRequest

ENTITY_NOT_SHOWN = 1
SHOWN_OR_NOT = (0, ENTITY_NOT_SHOWN)
UNKNOWN_ENTITY_DIAGNOSTIC = "is not defined in the workspace"

__all__ = ("Entity", "EntityField", "read_entity")


def read_entity(
    run_process: Callable[[ProcessRequest], ProcessRecord], root: Path, entity_type: str, name: str
) -> Entity:
    target = f"@{entity_type}.{name}"
    record = run_awawa(run_process, root, ("show", target, "--json", str(root)), SHOWN_OR_NOT)
    if record.exit_code == ENTITY_NOT_SHOWN:
        if UNKNOWN_ENTITY_DIAGNOSTIC in record.stderr:
            raise EntityNotDefined(f"{target} is not defined in {root}")
        raise CommandFailed(record.argv, record.exit_code, record.stderr)
    return decode_entity(name, json.loads(record.stdout))
