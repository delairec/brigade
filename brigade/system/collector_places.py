from dataclasses import dataclass
from pathlib import Path

from brigade.system.paths import Paths

PROJECT_COLLECTORS_DIRECTORY = Path(".brigade", "collectors")
MACHINE_COLLECTORS_DIRECTORY = "collectors"
EXECUTABLE_PREFIX = "brigade-collector-"
BUILT_IN_PACKAGE = "brigade.collectors"
PROJECT_SOURCE = "project"
MACHINE_SOURCE = "machine"
PATH_SOURCE = "PATH"
BUILT_IN_SOURCE = "built-in"


@dataclass(frozen=True)
class CollectorPlaces:
    project_directory: Path
    machine_directory: Path
    executable_search_path: str


def locate_collectors(project: Path, paths: Paths) -> CollectorPlaces:
    return CollectorPlaces(
        project_directory=project / PROJECT_COLLECTORS_DIRECTORY,
        machine_directory=paths.config_root / MACHINE_COLLECTORS_DIRECTORY,
        executable_search_path=paths.executable_search_path,
    )
