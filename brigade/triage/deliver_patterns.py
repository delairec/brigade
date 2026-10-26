from dataclasses import dataclass

from brigade.corpus.change_corpus_file import CorpusChange, change_corpus_file
from brigade.corpus.locate_corpus_lock import locate_corpus_lock
from brigade.corpus.read_entities import read_entities
from brigade.corpus.set_entity_status import set_entity_status
from brigade.ledger.append_event import append_event
from brigade.ledger.constraint_delivered import ConstraintDelivered
from brigade.registry.read_project_field import read_project_field
from brigade.runtime import Runtime
from brigade.studies.name_answer_file import name_answer_file
from brigade.triage.ratify_pattern import CONSTRAINT_TYPE, PATTERN_TYPE

DELIVERED_STATUS = "delivered"
PATTERN_REFERENCE_PREFIX = f"@{PATTERN_TYPE}."


@dataclass(frozen=True)
class WaveDelivery:
    project: str
    milestones: tuple[str, ...]


def _list_delivered_patterns(runtime: Runtime, delivery: WaveDelivery) -> tuple[str, ...]:
    return tuple(
        read_project_field(request, "FROM").removeprefix(PATTERN_REFERENCE_PREFIX)
        for request in read_entities(runtime.run_process, runtime.paths.config_root, "REQUEST")
        if read_project_field(request, "PROJECT") == f"@PROJECT.{delivery.project}"
        and read_project_field(request, "FROM")
        and read_project_field(request, "MILESTONE") in delivery.milestones
    )


def _list_delivered_constraints(runtime: Runtime, patterns: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(
        constraint.name
        for constraint in read_entities(runtime.run_process, runtime.paths.config_root, CONSTRAINT_TYPE)
        if read_project_field(constraint, "FROM").removeprefix(PATTERN_REFERENCE_PREFIX) in patterns
    )


def _set_delivered(text: str, entity_type: str, names: tuple[str, ...]) -> str:
    for name in names:
        text = set_entity_status(text, entity_type, name, DELIVERED_STATUS)
    return text


def deliver_patterns(runtime: Runtime, delivery: WaveDelivery) -> None:
    patterns = _list_delivered_patterns(runtime, delivery)
    if not patterns:
        return
    delivered = {PATTERN_TYPE: patterns, CONSTRAINT_TYPE: _list_delivered_constraints(runtime, patterns)}
    entity_types = tuple(entity_type for entity_type, names in delivered.items() if names)
    root = runtime.paths.config_root
    change_corpus_file(
        runtime.run_process,
        CorpusChange(
            repository=root,
            lock=locate_corpus_lock(runtime.paths.lock_directory, root),
            file_names=tuple(name_answer_file(entity_type) for entity_type in entity_types),
            describe_message=lambda: f"brigade tick: the patterns of {delivery.project} {DELIVERED_STATUS}",
            rewrite=lambda texts: tuple(
                _set_delivered(text, entity_type, delivered[entity_type])
                for text, entity_type in zip(texts, entity_types, strict=True)
            ),
        ),
    )
    constraints = delivered[CONSTRAINT_TYPE]
    for _ in constraints:
        append_event(runtime.paths, runtime.now, ConstraintDelivered(project=delivery.project))
