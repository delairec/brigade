from collections.abc import Callable
from pathlib import Path

from brigade.planning.read_plan import PlanEntity

FIELD_INDENT = "\t"
OPTIONAL_MARK = "// "
CONDITION_KEYWORD = "WHEN"


def _read_declared_fields(read_entity_template, root: Path, plan_entity: PlanEntity) -> tuple[str, ...] | None:
    template = read_entity_template(root, plan_entity.type, plan_entity.entity.name)
    if template is None:
        return None
    declarations = (
        line.removeprefix(FIELD_INDENT).removeprefix(OPTIONAL_MARK).split()[0]
        for line in template.splitlines()
        if line.startswith(FIELD_INDENT) and not line.startswith(FIELD_INDENT * 2)
    )
    return tuple(name for name in declarations if name != CONDITION_KEYWORD)


def list_undeclared(
    read_entity_template: Callable[[Path, str, str], str | None], root: Path, plan: tuple[PlanEntity, ...]
) -> list[str]:
    undeclared = []
    for plan_entity in plan:
        declared = _read_declared_fields(read_entity_template, root, plan_entity)
        if declared is None:
            undeclared.append(f"the type {plan_entity.type}")
            continue
        undeclared.extend(
            f"the field {field.name} of {plan_entity.type}"
            for field in plan_entity.entity.fields
            if field.name not in declared
        )
    return list(dict.fromkeys(undeclared))
