import importlib

from brigade.list_command_modules import COMMANDS_PACKAGE, list_command_modules


def list_command_paths() -> list[tuple[str, ...]]:
    return [importlib.import_module(f"{COMMANDS_PACKAGE}.{name}").COMMAND.path for name in list_command_modules()]
