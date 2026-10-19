from importlib.resources import files

COMMANDS_PACKAGE = "brigade.commands"
MODULE_SUFFIX = ".py"
PRIVATE_MODULE_PREFIX = "_"


def list_command_modules() -> list[str]:
    return sorted(
        entry.name.removesuffix(MODULE_SUFFIX)
        for entry in files(COMMANDS_PACKAGE).iterdir()
        if entry.name.endswith(MODULE_SUFFIX) and not entry.name.startswith(PRIVATE_MODULE_PREFIX)
    )
