import tomllib
from importlib.resources.abc import Traversable

from brigade.recipes.recipe_found import RecipeFound

RECIPE_SUFFIX = ".toml"


def read_recipe_files(directory: Traversable, source: str) -> list[RecipeFound]:
    if not directory.is_dir():
        return []
    return [
        RecipeFound(
            name=entry.name.removesuffix(RECIPE_SUFFIX),
            source=source,
            document=tomllib.loads(entry.read_text(encoding="utf-8")),
        )
        for entry in sorted(directory.iterdir(), key=lambda entry: entry.name)
        if entry.name.endswith(RECIPE_SUFFIX)
    ]
