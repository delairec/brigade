from dataclasses import dataclass


@dataclass(frozen=True)
class EntityField:
    name: str
    value: str


@dataclass(frozen=True)
class Entity:
    name: str
    fields: tuple[EntityField, ...]
