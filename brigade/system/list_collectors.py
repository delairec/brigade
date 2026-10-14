import os
from importlib.resources import files
from pathlib import Path

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

MODULE_SUFFIX = ".py"
PRIVATE_MODULE_PREFIX = "_"


def _list_executables(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(path for path in directory.iterdir() if is_executable(path))


def _list_search_path(search_path: str) -> list[str]:
    executables = (path for directory in search_path.split(os.pathsep) for path in _list_executables(Path(directory)))
    return sorted(
        {path.name.removeprefix(EXECUTABLE_PREFIX) for path in executables if path.name.startswith(EXECUTABLE_PREFIX)}
    )


def _list_built_ins() -> list[str]:
    names = (entry.name for entry in files(BUILT_IN_PACKAGE).iterdir())
    return sorted(
        name.removesuffix(MODULE_SUFFIX).replace("_", "-")
        for name in names
        if name.endswith(MODULE_SUFFIX) and not name.startswith(PRIVATE_MODULE_PREFIX)
    )


def list_collectors(places: CollectorPlaces) -> list[dict]:
    return [
        *({"name": path.name, "source": PROJECT_SOURCE} for path in _list_executables(places.project_directory)),
        *({"name": path.name, "source": MACHINE_SOURCE} for path in _list_executables(places.machine_directory)),
        *({"name": name, "source": PATH_SOURCE} for name in _list_search_path(places.executable_search_path)),
        *({"name": name, "source": BUILT_IN_SOURCE} for name in _list_built_ins()),
    ]
