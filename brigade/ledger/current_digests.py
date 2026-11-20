from dataclasses import dataclass


@dataclass(frozen=True)
class CurrentDigests:
    role: str | None
    procedures: dict
