from collections.abc import Callable
from pathlib import Path

from brigade.planning.read_plan import PlanEntity
from brigade.system.run_process import ProcessRecord, ProcessRequest

AWAWA_TIMEOUT_S = 30.0
TYPE_DECLARED = 0
TYPE_DECLARED_OR_NOT = (TYPE_DECLARED, 1)
FIELD_INDENT = "\t"
OPTIONAL_MARK = "// "
CONDITION_KEYWORD = "WHEN"


def _read_declared_fields(run_process, root: Path, plan_entity: PlanEntity) -> tuple[str, ...] | None:
    record = run_process(
        ProcessRequest(
            argv=("awawa", "new", plan_entity.type, plan_entity.entity.name, str(root)),
            cwd=str(root),
            timeout_s=AWAWA_TIMEOUT_S,
            acceptable_exit_codes=TYPE_DECLARED_OR_NOT,
        )
    )
    if record.exit_code != TYPE_DECLARED:
        return None
    declarations = (
        line.removeprefix(FIELD_INDENT).removeprefix(OPTIONAL_MARK).split()[0]
        for line in record.stdout.splitlines()
        if line.startswith(FIELD_INDENT) and not line.startswith(FIELD_INDENT * 2)
    )
    return tuple(name for name in declarations if name != CONDITION_KEYWORD)


def list_undeclared(
    run_process: Callable[[ProcessRequest], ProcessRecord], root: Path, plan: tuple[PlanEntity, ...]
) -> list[str]:
    undeclared = []
    for plan_entity in plan:
        declared = _read_declared_fields(run_process, root, plan_entity)
        if declared is None:
            undeclared.append(f"the type {plan_entity.type}")
            continue
        undeclared.extend(
            f"the field {field.name} of {plan_entity.type}"
            for field in plan_entity.entity.fields
            if field.name not in declared
        )
    return list(dict.fromkeys(undeclared))
