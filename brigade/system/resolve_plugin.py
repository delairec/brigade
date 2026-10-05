import importlib
from types import ModuleType

from brigade.errors import BrigadeError

BUILT_IN_PLUGIN_PACKAGES = {"forge": "brigade.adapters.forges"}


def resolve_plugin(kind: str, name: str) -> ModuleType:
    package = BUILT_IN_PLUGIN_PACKAGES.get(kind)
    if package is None:
        raise BrigadeError(f"no plugin kind {kind}")
    if not name.isidentifier():
        raise BrigadeError(f"no {kind} plugin {name}")
    module_name = f"{package}.{name}"
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError as error:
        if error.name != module_name:
            raise
        raise BrigadeError(f"no {kind} plugin {name}") from None
