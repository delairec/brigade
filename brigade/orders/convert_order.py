from dataclasses import dataclass

from brigade.corpus.read_entity import Entity

PROJECT_REFERENCE_PREFIX = "@PROJECT."


@dataclass(frozen=True)
class Order:
    name: str
    recipe: str
    project: str | None
    text: str | None
    params: tuple[str, ...]
    every: str | None
    status: str

    def to_document(self) -> dict:
        return {
            "name": self.name,
            "recipe": self.recipe,
            "project": self.project,
            "text": self.text,
            "params": list(self.params),
            "every": self.every,
            "status": self.status,
        }


def _read_values(entity: Entity, field_name: str) -> tuple[str, ...]:
    return tuple(field.value for field in entity.fields if field.name == field_name)


def _read_optional_value(entity: Entity, field_name: str) -> str | None:
    return next(iter(_read_values(entity, field_name)), None)


def convert_order(entity: Entity) -> Order:
    project = _read_optional_value(entity, "PROJECT")
    return Order(
        name=entity.name,
        recipe=_read_values(entity, "RECIPE")[0],
        project=None if project is None else project.removeprefix(PROJECT_REFERENCE_PREFIX),
        text=_read_optional_value(entity, "TEXT"),
        params=_read_values(entity, "PARAM"),
        every=_read_optional_value(entity, "EVERY"),
        status=_read_values(entity, "STATUS")[0],
    )
