from dataclasses import dataclass
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path

PROJECT_RECIPES_DIRECTORY = Path(".brigade", "recipes")
MACHINE_RECIPES_DIRECTORY = "recipes"
BUILT_IN_RECIPES = files("brigade.recipes") / "data"


@dataclass(frozen=True)
class RecipePlaces:
    project_corpus: Path | None
    project_directory: Path
    machine_directory: Path
    built_ins: Traversable
