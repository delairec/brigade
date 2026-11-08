from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class TickForge:
    read_environment: Callable[[str], dict]
    list_check_runs: Callable[[str, str], list[dict]]
