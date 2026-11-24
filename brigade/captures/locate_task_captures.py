from pathlib import Path

from brigade.system.paths import Paths

CAPTURES_DIRECTORY = "captures"


def locate_task_captures(paths: Paths, project: str, task: str, head: str) -> Path:
    return paths.state_root / CAPTURES_DIRECTORY / project / task / head
