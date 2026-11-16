from dataclasses import dataclass


@dataclass(frozen=True)
class RecipeFound:
    name: str
    source: str
    document: dict
