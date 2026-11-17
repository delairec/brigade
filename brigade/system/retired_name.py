from dataclasses import dataclass


@dataclass(frozen=True)
class RetiredName:
    old: str
    new: str
