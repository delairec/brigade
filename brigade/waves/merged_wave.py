from dataclasses import dataclass


@dataclass(frozen=True)
class MergedWave:
    wave: str
    pr: int
