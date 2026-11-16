from dataclasses import dataclass
from pathlib import Path

from brigade.system.paths import Paths

PROJECT_CHECKS_DIRECTORY = Path(".brigade", "checks")
MACHINE_CHECKS_DIRECTORY = "checks"
EXECUTABLE_PREFIX = "brigade-check-"
BUILT_IN_PACKAGE = "brigade.checks"


@dataclass(frozen=True)
class CheckPlaces:
    project_directory: Path
    machine_directory: Path
    executable_search_path: str


def locate_checks(project: Path, paths: Paths) -> CheckPlaces:
    return CheckPlaces(
        project_directory=project / PROJECT_CHECKS_DIRECTORY,
        machine_directory=paths.config_root / MACHINE_CHECKS_DIRECTORY,
        executable_search_path=paths.executable_search_path,
    )
