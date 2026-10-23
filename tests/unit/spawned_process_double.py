from dataclasses import dataclass


@dataclass(frozen=True)
class SpawnedProcessDouble:
    pid: int
