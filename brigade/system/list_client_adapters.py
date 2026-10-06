import importlib
import os
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

from brigade.system.resolve_plugin import (
    CLIENT_ENTRY_POINT,
    CLIENT_EXECUTABLE_PREFIX,
    CLIENT_NAME_PATTERN,
    CLIENT_PACKAGES,
)

SUPPORTED_CLIENT = "supported_client"
TEST_SUITE = "test_suite"
PACKAGE_AUDIENCES = dict(zip(CLIENT_PACKAGES, (SUPPORTED_CLIENT, TEST_SUITE)))
MODULE_SUFFIX = ".py"
PRIVATE_MODULE_PREFIX = "_"
MODULE_WORD_SEPARATOR = "_"
NAME_WORD_SEPARATOR = "-"


@dataclass(frozen=True)
class ClientAdapter:
    name: str
    audience: str


def _is_executable_file(path: Path) -> bool:
    return path.is_file() and os.access(path, os.X_OK)


def _list_directory(directory: str) -> list[Path]:
    try:
        return sorted(Path(directory).iterdir())
    except OSError:
        return []


def _name_executable_adapter(path: Path):
    if not path.name.startswith(CLIENT_EXECUTABLE_PREFIX):
        return None
    name = path.name[len(CLIENT_EXECUTABLE_PREFIX) :]
    if not CLIENT_NAME_PATTERN.fullmatch(name) or not _is_executable_file(path):
        return None
    return name


def _list_executable_names(search_path: str) -> list[str]:
    names = (
        _name_executable_adapter(path)
        for directory in search_path.split(os.pathsep)
        if directory
        for path in _list_directory(directory)
    )
    return [name for name in names if name is not None]


def _list_module_basenames(package: str) -> list[str]:
    return sorted(
        entry.name[: -len(MODULE_SUFFIX)]
        for entry in files(package).iterdir()
        if entry.name.endswith(MODULE_SUFFIX) and not entry.name.startswith(PRIVATE_MODULE_PREFIX)
    )


def _list_built_in_adapters(package: str) -> list[ClientAdapter]:
    return [
        ClientAdapter(
            name=basename.replace(MODULE_WORD_SEPARATOR, NAME_WORD_SEPARATOR), audience=PACKAGE_AUDIENCES[package]
        )
        for basename in _list_module_basenames(package)
        if hasattr(importlib.import_module(f"{package}.{basename}"), CLIENT_ENTRY_POINT)
    ]


def list_client_adapters(runtime) -> tuple[ClientAdapter, ...]:
    candidates = [
        *(
            ClientAdapter(name=name, audience=SUPPORTED_CLIENT)
            for name in _list_executable_names(runtime.paths.executable_search_path)
        ),
        *(adapter for package in CLIENT_PACKAGES for adapter in _list_built_in_adapters(package)),
    ]
    adapters = {}
    for candidate in candidates:
        adapters.setdefault(candidate.name, candidate)
    return tuple(adapters.values())
