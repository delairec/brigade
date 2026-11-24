from brigade.corpus.read_entities import Entity
from brigade.registry.read_project_field import read_project_field
from brigade.triage.read_new_pattern import PATTERN_TYPE

PATTERN_REFERENCE_PREFIX = f"@{PATTERN_TYPE}."
RECURRENCE_MARK = "_recurs"
NAME_SEPARATOR = "_"


def _is_repeated_by_stem(name: str, stem: str) -> bool:
    return RECURRENCE_MARK not in name and (name == stem or name.startswith(stem + NAME_SEPARATOR))


def read_repeated_pattern(pattern: Entity, names: list[str]) -> str | None:
    repeated = read_project_field(pattern, "REPEATS")
    if repeated is not None:
        return repeated.removeprefix(PATTERN_REFERENCE_PREFIX)
    stem, mark, _ = pattern.name.partition(RECURRENCE_MARK)
    if not mark:
        return None
    return next((name for name in names if _is_repeated_by_stem(name, stem)), None)
