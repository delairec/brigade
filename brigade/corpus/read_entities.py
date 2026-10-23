import json
from collections.abc import Callable
from pathlib import Path

from brigade.corpus.read_entity import Entity, EntityField, read_entity
from brigade.corpus.run_awawa import SUCCESS, run_awawa
from brigade.system.run_process import ProcessRecord, ProcessRequest

UNREADABLE_NAME = "?"

__all__ = ("Entity", "EntityField", "read_entities")


def read_entities(
    run_process: Callable[[ProcessRequest], ProcessRecord], root: Path, entity_type: str, *conditions: str
) -> tuple[Entity, ...]:
    filters = tuple(argument for condition in conditions for argument in ("--where", condition))
    record = run_awawa(run_process, root, ("status", entity_type, *filters, "--json", str(root)), SUCCESS)
    status = json.loads(record.stdout)
    names = sorted(
        entity["name"]
        for entity in status["entities"]
        if entity["type"] == entity_type and entity["name"] != UNREADABLE_NAME
    )
    return tuple(read_entity(run_process, root, entity_type, name) for name in names)
