from dataclasses import dataclass


@dataclass(frozen=True)
class ViewRequest:
    view: str
    entity_type: str | None = None
    field: str | None = None
    filters: tuple[str, ...] = ()
    search: str | None = None
    entity: str | None = None
