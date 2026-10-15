import os
from pathlib import Path


def is_executable(path: Path) -> bool:
    return path.is_file() and os.access(path, os.X_OK)
