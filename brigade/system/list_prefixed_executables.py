import os
from pathlib import Path

from brigade.system.list_executables import list_executables


def list_prefixed_executables(search_path: str, prefix: str) -> list[str]:
    executables = (path for directory in search_path.split(os.pathsep) for path in list_executables(Path(directory)))
    return sorted({path.name.removeprefix(prefix) for path in executables if path.name.startswith(prefix)})
