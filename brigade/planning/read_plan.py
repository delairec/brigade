import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.read_entity import Entity, EntityField
from brigade.system.run_process import ProcessRecord, ProcessRequest

AWAWA_TIMEOUT_S = 30.0
QUOTE = '"'


@dataclass(frozen=True)
class PlanEntity:
    type: str
    entity: Entity


def _show(run_process: Callable[[ProcessRequest], ProcessRecord], plan_file: Path, target: str) -> dict:
    record = run_process(
        ProcessRequest(
            argv=("awawa", "show", target, "--json", str(plan_file)),
            cwd=str(plan_file.parent),
            timeout_s=AWAWA_TIMEOUT_S,
        )
    )
    return json.loads(record.stdout)


def _decode_atom(atom: str) -> str:
    if atom.startswith(QUOTE):
        return json.loads(atom)
    return atom


def _read_plan_entity(run_process, plan_file: Path, entity_type: str, name: str) -> PlanEntity:
    shown = _show(run_process, plan_file, f"@{entity_type}.{name}")
    fields = tuple(
        EntityField(name=field["name"], value="".join(_decode_atom(atom) for atom in field["atoms"]))
        for field in shown["fields"]
    )
    return PlanEntity(type=entity_type, entity=Entity(name=name, fields=fields))


def read_plan(run_process: Callable[[ProcessRequest], ProcessRecord], plan_file: Path) -> tuple[PlanEntity, ...]:
    listed = _show(run_process, plan_file, str(plan_file))
    return tuple(
        _read_plan_entity(run_process, plan_file, entity["type"], entity["name"]) for entity in listed["entities"]
    )
