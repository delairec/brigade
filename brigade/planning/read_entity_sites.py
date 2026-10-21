from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class EntitySite:
    type: str
    name: str
    file: str
    line: int


def read_entity_sites(
    read_awawa_document: Callable[[Path, tuple[str, ...]], dict], root: Path
) -> tuple[EntitySite, ...]:
    return tuple(
        EntitySite(
            type=entity["type"],
            name=entity["name"],
            file=(root / entity["file"]).resolve().relative_to(root.resolve()).as_posix(),
            line=entity["line"],
        )
        for entity in read_awawa_document(root, ("status",))["entities"]
    )
