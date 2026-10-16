from dataclasses import dataclass

from brigade.corpus.read_entity import Entity, read_entity
from brigade.errors import BrigadeError, EntityNotDefined
from brigade.registry.require_operational_corpus import require_operational_corpus
from brigade.runtime import Runtime

ENTITY_TYPE = "STUDY"
PROJECT_REFERENCE_PREFIX = "@PROJECT."


@dataclass(frozen=True)
class Study:
    name: str
    project: str | None
    question: str | None
    collectors: tuple[str, ...]
    slot: str
    output: str
    answer_type: str


def _read_values(entity: Entity, field_name: str) -> tuple[str, ...]:
    return tuple(field.value for field in entity.fields if field.name == field_name)


def _read_question(entity: Entity) -> str | None:
    questions = _read_values(entity, "QUESTION")
    if not questions:
        return None
    return questions[0]


def _read_project(entity: Entity) -> str | None:
    references = _read_values(entity, "PROJECT")
    if not references:
        return None
    return references[0].removeprefix(PROJECT_REFERENCE_PREFIX)


def read_study(runtime: Runtime, name: str) -> Study:
    require_operational_corpus(runtime.paths)
    try:
        entity = read_entity(runtime.run_process, runtime.paths.config_root, ENTITY_TYPE, name)
    except EntityNotDefined:
        raise BrigadeError(f"@{ENTITY_TYPE}.{name} is not defined in the operational corpus") from None
    return Study(
        name=name,
        project=_read_project(entity),
        question=_read_question(entity),
        collectors=_read_values(entity, "COLLECTOR"),
        slot=_read_values(entity, "SLOT")[0],
        output=_read_values(entity, "OUTPUT")[0],
        answer_type=_read_values(entity, "ANSWER")[0],
    )
