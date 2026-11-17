from __future__ import annotations

import importlib
import importlib.util
import json
import re
import shutil
from dataclasses import dataclass
from typing import TYPE_CHECKING

from brigade.errors import BrigadeError
from brigade.system.check_places import BUILT_IN_PACKAGE, EXECUTABLE_PREFIX, CheckPlaces
from brigade.system.check_shapes import CHECK_DOCUMENT_SHAPE
from brigade.system.collector_places import BUILT_IN_SOURCE, MACHINE_SOURCE, PATH_SOURCE, PROJECT_SOURCE
from brigade.system.is_executable import is_executable
from brigade.system.run_process import EVERY_EXIT_CODE, ProcessRequest
from brigade.system.validate_document import DocumentInvalid, validate_document

if TYPE_CHECKING:
    from brigade.runtime import Runtime

CHECK_NAME_PATTERN = re.compile(r"[a-z][a-z0-9_-]*")
CHECK_TIMEOUT_S = 600.0


def _read_answer(name: str, document: object) -> dict:
    try:
        validate_document(document, CHECK_DOCUMENT_SHAPE)
    except DocumentInvalid as error:
        raise BrigadeError(f"check {name} answered no check document: {error}") from None
    return document


@dataclass(frozen=True)
class ExecutableCheck:
    name: str
    source: str
    command: str

    def judge(self, subject: dict, runtime: Runtime) -> dict:
        record = runtime.run_process(
            ProcessRequest(
                argv=(self.command,),
                cwd=subject["project"],
                timeout_s=CHECK_TIMEOUT_S,
                acceptable_exit_codes=EVERY_EXIT_CODE,
                stdin=json.dumps(subject),
            )
        )
        try:
            document = json.loads(record.stdout)
        except ValueError:
            raise BrigadeError(f"check {self.name} answered no JSON document") from None
        return _read_answer(self.name, document)


@dataclass(frozen=True)
class BuiltInCheck:
    name: str
    source: str
    command: str
    module: object

    def judge(self, subject: dict, runtime: Runtime) -> dict:
        return _read_answer(self.name, self.module.check(subject, runtime))


def _find_executable(name: str, places: CheckPlaces) -> ExecutableCheck | None:
    for source, directory in ((PROJECT_SOURCE, places.project_directory), (MACHINE_SOURCE, places.machine_directory)):
        if is_executable(directory / name):
            return ExecutableCheck(name=name, source=source, command=str(directory / name))
    executable = shutil.which(f"{EXECUTABLE_PREFIX}{name}", path=places.executable_search_path)
    if executable is None:
        return None
    return ExecutableCheck(name=name, source=PATH_SOURCE, command=executable)


def _find_built_in(name: str) -> BuiltInCheck | None:
    module_name = f"{BUILT_IN_PACKAGE}.{name}"
    if importlib.util.find_spec(module_name) is None:
        return None
    return BuiltInCheck(
        name=name, source=BUILT_IN_SOURCE, command=module_name, module=importlib.import_module(module_name)
    )


def resolve_check(name: str, places: CheckPlaces) -> ExecutableCheck | BuiltInCheck:
    check = None
    if CHECK_NAME_PATTERN.fullmatch(name):
        check = _find_executable(name, places) or _find_built_in(name)
    if check is None:
        raise BrigadeError(
            f"no check {name} in {places.project_directory}, in {places.machine_directory},"
            f" as {EXECUTABLE_PREFIX}{name} on PATH or among the built-ins of brigade/checks"
        )
    return check
