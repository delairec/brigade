import json
from collections.abc import Callable
from pathlib import Path

from brigade.corpus.read_entity import Entity, EntityField, read_entity
from brigade.system.run_process import ProcessRecord, ProcessRequest

AWAWA_TIMEOUT_S = 30.0
UNREADABLE_NAME = "?"

__all__ = ("Entity", "EntityField", "read_entities")


def read_entities(
    run_process: Callable[[ProcessRequest], ProcessRecord], root: Path, entity_type: str
) -> tuple[Entity, ...]:
    record = run_process(
        ProcessRequest(
            argv=("awawa", "status", entity_type, "--json", str(root)), cwd=str(root), timeout_s=AWAWA_TIMEOUT_S
        )
    )
    status = json.loads(record.stdout)
    names = sorted(
        entity["name"]
        for entity in status["entities"]
        if entity["type"] == entity_type and entity["name"] != UNREADABLE_NAME
    )
    return tuple(read_entity(run_process, root, entity_type, name) for name in names)
