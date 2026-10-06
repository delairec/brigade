from pathlib import Path

from brigade.system.paths import Paths


def locate_unit_directory(paths: Paths) -> Path:
    return paths.config_root.parent / "systemd" / "user"
