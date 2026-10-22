from dataclasses import dataclass

from brigade.corpus.read_entity import Entity

PROJECT_REFERENCE_PREFIX = "@PROJECT."


@dataclass(frozen=True)
class Study:
    name: str
    project: str | None
    question: str | None
    collectors: tuple[str, ...]
    slot: str
    every: str | None
    output: str
    answer_type: str
    status: str
    wave: str | None = None


def _read_values(entity: Entity, field_name: str) -> tuple[str, ...]:
    return tuple(field.value for field in entity.fields if field.name == field_name)


def _read_optional_value(entity: Entity, field_name: str) -> str | None:
    values = _read_values(entity, field_name)
    if not values:
        return None
    return values[0]


def convert_study(entity: Entity) -> Study:
    project = _read_optional_value(entity, "PROJECT")
    return Study(
        name=entity.name,
        project=None if project is None else project.removeprefix(PROJECT_REFERENCE_PREFIX),
        question=_read_optional_value(entity, "QUESTION"),
        collectors=_read_values(entity, "COLLECTOR"),
        slot=_read_values(entity, "SLOT")[0],
        every=_read_optional_value(entity, "EVERY"),
        output=_read_values(entity, "OUTPUT")[0],
        answer_type=_read_values(entity, "ANSWER")[0],
        status=_read_values(entity, "STATUS")[0],
    )
