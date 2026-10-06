import importlib
import json
import re
import shutil
from dataclasses import dataclass
from typing import Callable

from brigade.errors import BrigadeError
from brigade.system.run_process import ProcessRecord, ProcessRequest

BUILT_IN_PLUGIN_PACKAGES = {"forge": "brigade.adapters.forges", "scheduler": "brigade.adapters.schedulers"}
CLIENT_PACKAGES = ("brigade.adapters.clients", "brigade.adapters.test_clients")
BUILT_IN_ENTRY_POINTS = {"forge": "describe_account", "scheduler": "install"}
CLIENT_NAME_PATTERN = re.compile(r"[a-z][a-z0-9-]*")
CLIENT_EXECUTABLE_PREFIX = "brigade-client-"
CLIENT_EXECUTABLE_DIRECTORY = "/"
CLIENT_EXECUTABLE_TIMEOUT_S = 30.0
CLIENT_ENTRY_POINT = "answer"


@dataclass(frozen=True)
class ClientExecutableCaller:
    name: str
    executable: str
    run_process: Callable[[ProcessRequest], ProcessRecord]

    def answer(self, operation: str, request: dict) -> dict:
        record = self.run_process(
            ProcessRequest(
                argv=(self.executable, operation),
                cwd=CLIENT_EXECUTABLE_DIRECTORY,
                timeout_s=CLIENT_EXECUTABLE_TIMEOUT_S,
                stdin=json.dumps(request),
            )
        )
        try:
            return json.loads(record.stdout)
        except ValueError:
            raise BrigadeError(f"client adapter {self.name} answered {operation} with no JSON document") from None


def _import_module(package: str, module_basename: str):
    module_name = f"{package}.{module_basename}"
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError as error:
        if error.name != module_name:
            raise
        return None


def _resolve_built_in(kind: str, name: str):
    plugin = _import_module(BUILT_IN_PLUGIN_PACKAGES[kind], name) if name.isidentifier() else None
    if not hasattr(plugin, BUILT_IN_ENTRY_POINTS[kind]):
        raise BrigadeError(f"no {kind} plugin {name}")
    return plugin


def _resolve_client(name: str, runtime):
    missing = BrigadeError(f"no client adapter {name}: no built-in module and no {CLIENT_EXECUTABLE_PREFIX}{name} on PATH")
    if not CLIENT_NAME_PATTERN.fullmatch(name):
        raise missing
    executable = shutil.which(f"{CLIENT_EXECUTABLE_PREFIX}{name}", path=runtime.paths.executable_search_path)
    if executable is not None:
        return ClientExecutableCaller(name=name, executable=executable, run_process=runtime.run_process)
    modules = (_import_module(package, name.replace("-", "_")) for package in CLIENT_PACKAGES)
    plugin = next((module for module in modules if hasattr(module, CLIENT_ENTRY_POINT)), None)
    if plugin is None:
        raise missing
    return plugin


def resolve_plugin(kind: str, name: str, runtime):
    if kind in BUILT_IN_ENTRY_POINTS:
        return _resolve_built_in(kind, name)
    if kind == "client":
        return _resolve_client(name, runtime)
    raise BrigadeError(f"no plugin kind {kind}")
