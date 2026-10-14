import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.system.run_process import ProcessRecord, ProcessRequest

AWAWA_TIMEOUT_S = 30.0


@dataclass(frozen=True)
class EntitySite:
    type: str
    name: str
    file: str
    line: int


def read_entity_sites(run_process: Callable[[ProcessRequest], ProcessRecord], root: Path) -> tuple[EntitySite, ...]:
    record = run_process(
        ProcessRequest(argv=("awawa", "status", "--json", str(root)), cwd=str(root), timeout_s=AWAWA_TIMEOUT_S)
    )
    return tuple(
        EntitySite(
            type=entity["type"],
            name=entity["name"],
            file=(root / entity["file"]).resolve().relative_to(root.resolve()).as_posix(),
            line=entity["line"],
        )
        for entity in json.loads(record.stdout)["entities"]
    )
