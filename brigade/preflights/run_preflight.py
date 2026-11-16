import tomllib
from dataclasses import dataclass
from datetime import date
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path

from brigade.collecting.collect_document import CollectionRequest, collect_document
from brigade.collecting.collector_environment import CollectorInputs
from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.errors import BrigadeError
from brigade.runtime import Runtime
from brigade.system.check_places import locate_checks
from brigade.system.check_shapes import FAILED, PASSED
from brigade.system.collector_places import locate_collectors
from brigade.system.document_shapes import SCHEMA_VERSION, TEXT
from brigade.system.resolve_check import resolve_check
from brigade.system.resolve_collector import resolve_collector
from brigade.system.validate_document import Field, validate_document

BUILT_IN_PREFLIGHTS = files("brigade.preflights") / "data"
PREFLIGHT_SUFFIX = ".toml"
SUBJECT_SCHEMA_VERSION = 1
SCHEMA_VERSION_KEY = "schema_version"
BEGINNING = date(1970, 1, 1)
NO_PARAMETERS = {}
STEP = Field(kinds=(dict,), fields={"name": TEXT, "parameters": Field(kinds=(dict,), optional=True)})
PREFLIGHT_SHAPE = {
    "schema_version": SCHEMA_VERSION,
    "name": TEXT,
    "description": TEXT,
    "collectors": Field(kinds=(list,), items=STEP),
    "checks": Field(kinds=(list,), items=STEP),
}


@dataclass(frozen=True)
class PreflightRun:
    name: str
    project: Path
    parameters: dict
    equipment: CollectorEquipment
    preflights: Traversable


@dataclass(frozen=True)
class PreflightOutcome:
    verdict: str
    checks: list
    collected: dict


def _read_preflight(run: PreflightRun) -> dict:
    file = run.preflights / f"{run.name}{PREFLIGHT_SUFFIX}"
    if not file.is_file():
        raise BrigadeError(f"no preflight {run.name}: no {run.name}{PREFLIGHT_SUFFIX} in {run.preflights}")
    document = tomllib.loads(file.read_text(encoding="utf-8"))
    validate_document(document, PREFLIGHT_SHAPE)
    return document


def _merge_parameters(step: dict, run: PreflightRun) -> dict:
    return {**step.get("parameters", NO_PARAMETERS), **run.parameters}


def _collect(step: dict, run: PreflightRun, runtime: Runtime) -> dict:
    collector = resolve_collector(step["name"], locate_collectors(run.project, runtime.paths))
    inputs = CollectorInputs(project=run.project, since=BEGINNING, parameters=_merge_parameters(step, run))
    request = CollectionRequest(inputs=inputs, refresh=False, equipment=run.equipment)
    return collect_document(collector, request, runtime).document


def _judge(step: dict, run: PreflightRun, collected: dict, runtime: Runtime) -> dict:
    check = resolve_check(step["name"], locate_checks(run.project, runtime.paths))
    subject = {
        "schema_version": SUBJECT_SCHEMA_VERSION,
        "project": str(run.project),
        "parameters": _merge_parameters(step, run),
        "collected": collected,
    }
    answer = check.judge(subject, runtime)
    return {key: value for key, value in answer.items() if key != SCHEMA_VERSION_KEY}


def run_preflight(run: PreflightRun, runtime: Runtime) -> PreflightOutcome:
    preflight = _read_preflight(run)
    collected = {step["name"]: _collect(step, run, runtime) for step in preflight["collectors"]}
    checks = [_judge(step, run, collected, runtime) for step in preflight["checks"]]
    verdict = FAILED if any(check["verdict"] == FAILED for check in checks) else PASSED
    return PreflightOutcome(verdict=verdict, checks=checks, collected=collected)
