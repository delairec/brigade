from importlib.resources import files
from importlib.resources.abc import Traversable

SHIPPED_ROLES = files("brigade.roles") / "data"
ROLE_FILE_SUFFIX = ".md"


def _name_entry(entry: Traversable) -> str:
    return entry.name


def list_built_in_role_files() -> tuple[Traversable, ...]:
    role_files = (entry for entry in SHIPPED_ROLES.iterdir() if entry.name.endswith(ROLE_FILE_SUFFIX))
    return tuple(sorted(role_files, key=_name_entry))
