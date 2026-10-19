import importlib
from importlib.resources import files

MODULE_SUFFIX = ".py"
PRIVATE_MODULE_PREFIX = "_"


def _name_after(path: tuple[str, ...]) -> str:
    return "_".join(path).replace("-", "_")


def _is_named_after_its_path(name: str, command) -> bool:
    if command.render_passed_stderr is None:
        return name == _name_after(command.path)
    return name.startswith(f"{_name_after(command.path)}_")


def _describe_misnaming(package: str, name: str) -> list[str]:
    command = importlib.import_module(f"{package}.{name}").COMMAND
    if _is_named_after_its_path(name, command):
        return []
    return [f"{package}.{name} declares brigade {' '.join(command.path)}"]


def find_misnamed_command_modules(package: str) -> list[str]:
    names = sorted(
        entry.name.removesuffix(MODULE_SUFFIX)
        for entry in files(package).iterdir()
        if entry.name.endswith(MODULE_SUFFIX) and not entry.name.startswith(PRIVATE_MODULE_PREFIX)
    )
    return [misnaming for name in names for misnaming in _describe_misnaming(package, name)]
