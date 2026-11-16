from pathlib import Path

from tests.unit.create_recipe_answers import create_recipe_answers


def create_recipe_outputs(corpus: Path, recipes: dict[str, tuple[tuple[str, ...], ...]]) -> dict:
    return {argv: answer.stdout for argv, answer in create_recipe_answers(corpus, recipes).items()}
