from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PlanPublication:
    repository: Path
    project: str
    base: str
    branch: str
    title: str
    body: str
    forge: object
    forge_name: str
    read_environment: Callable[[str], dict]
