from __future__ import annotations

import importlib
import importlib.util
import json
import re
import shutil
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from brigade.collecting.collector_environment import PROJECT_PATH_VARIABLE
from brigade.errors import BrigadeError
from brigade.system.collector_places import (
    BUILT_IN_PACKAGE,
    BUILT_IN_SOURCE,
    EXECUTABLE_PREFIX,
    MACHINE_SOURCE,
    PATH_SOURCE,
    PROJECT_SOURCE,
    CollectorPlaces,
)
from brigade.system.is_executable import is_executable
from brigade.system.run_process import EVERY_EXIT_CODE, ProcessRequest

if TYPE_CHECKING:
    from brigade.collecting.collector_equipment import CollectorEquipment
    from brigade.runtime import Runtime

COLLECTOR_NAME_PATTERN = re.compile(r"[a-z][a-z0-9-]*")
COLLECTOR_TIMEOUT_S = 600.0
COMPLETE_EXIT_CODE = 0
FAILED_EXIT_CODE = 1
NO_OUTPUT = ""


@dataclass(frozen=True)
class CollectorAnswer:
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int


@dataclass(frozen=True)
class ExecutableCollector:
    name: str
    source: str
    command: str

    def collect(self, environment: dict, runtime: Runtime, equipment: CollectorEquipment) -> CollectorAnswer:
        record = runtime.run_process(
            ProcessRequest(
                argv=(self.command,),
                cwd=environment[PROJECT_PATH_VARIABLE],
                timeout_s=COLLECTOR_TIMEOUT_S,
                acceptable_exit_codes=EVERY_EXIT_CODE,
                environment=environment,
            )
        )
        return CollectorAnswer(
            exit_code=record.exit_code, stdout=record.stdout, stderr=record.stderr, duration_ms=record.duration_ms
        )


def _measure_since(started: float) -> int:
    return round((time.monotonic() - started) * 1000)


@dataclass(frozen=True)
class BuiltInCollector:
    name: str
    source: str
    command: str
    module: object

    def collect(self, environment: dict, runtime: Runtime, equipment: CollectorEquipment) -> CollectorAnswer:
        started = time.monotonic()
        try:
            document = self.module.collect(environment, runtime, equipment)
        except BrigadeError as error:
            return CollectorAnswer(
                exit_code=FAILED_EXIT_CODE, stdout=NO_OUTPUT, stderr=f"{error}\n", duration_ms=_measure_since(started)
            )
        return CollectorAnswer(
            exit_code=COMPLETE_EXIT_CODE,
            stdout=json.dumps(document),
            stderr=NO_OUTPUT,
            duration_ms=_measure_since(started),
        )


def _find_executable(name: str, places: CollectorPlaces) -> ExecutableCollector | None:
    for source, directory in ((PROJECT_SOURCE, places.project_directory), (MACHINE_SOURCE, places.machine_directory)):
        if is_executable(directory / name):
            return ExecutableCollector(name=name, source=source, command=str(directory / name))
    executable = shutil.which(f"{EXECUTABLE_PREFIX}{name}", path=places.executable_search_path)
    if executable is None:
        return None
    return ExecutableCollector(name=name, source=PATH_SOURCE, command=executable)


def _find_built_in(name: str) -> BuiltInCollector | None:
    module_name = f"{BUILT_IN_PACKAGE}.{name.replace('-', '_')}"
    if importlib.util.find_spec(module_name) is None:
        return None
    return BuiltInCollector(
        name=name, source=BUILT_IN_SOURCE, command=module_name, module=importlib.import_module(module_name)
    )


def resolve_collector(name: str, places: CollectorPlaces) -> ExecutableCollector | BuiltInCollector:
    collector = None
    if COLLECTOR_NAME_PATTERN.fullmatch(name):
        collector = _find_executable(name, places) or _find_built_in(name)
    if collector is None:
        raise BrigadeError(
            f"no collector {name} in {places.project_directory}, in {places.machine_directory},"
            f" as {EXECUTABLE_PREFIX}{name} on PATH or among the built-ins of brigade/collectors"
        )
    return collector
