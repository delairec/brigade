from importlib.resources import files

from brigade.system.collector_places import (
    BUILT_IN_PACKAGE,
    BUILT_IN_SOURCE,
    EXECUTABLE_PREFIX,
    MACHINE_SOURCE,
    PATH_SOURCE,
    PROJECT_SOURCE,
    CollectorPlaces,
)
from brigade.system.list_executables import list_executables
from brigade.system.list_prefixed_executables import list_prefixed_executables

MODULE_SUFFIX = ".py"
PRIVATE_MODULE_PREFIX = "_"


def _list_built_ins() -> list[str]:
    names = (entry.name for entry in files(BUILT_IN_PACKAGE).iterdir())
    return sorted(
        name.removesuffix(MODULE_SUFFIX).replace("_", "-")
        for name in names
        if name.endswith(MODULE_SUFFIX) and not name.startswith(PRIVATE_MODULE_PREFIX)
    )


def list_collectors(places: CollectorPlaces) -> list[dict]:
    return [
        *({"name": path.name, "source": PROJECT_SOURCE} for path in list_executables(places.project_directory)),
        *({"name": path.name, "source": MACHINE_SOURCE} for path in list_executables(places.machine_directory)),
        *(
            {"name": name, "source": PATH_SOURCE}
            for name in list_prefixed_executables(places.executable_search_path, EXECUTABLE_PREFIX)
        ),
        *({"name": name, "source": BUILT_IN_SOURCE} for name in _list_built_ins()),
    ]
