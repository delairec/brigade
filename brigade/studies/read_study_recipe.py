import tomllib

from brigade.recipes.recipe_places import BUILT_IN_RECIPES
from brigade.studies.read_study import Study

STUDY_RECIPE_FILE = "study.toml"
COLLECT_KIND = "collect"


def _expand_step(step: dict, study: Study) -> list[dict]:
    if step["kind"] != COLLECT_KIND:
        return [step]
    return [{**step, "collector": line} for line in study.collectors]


def read_study_recipe(study: Study) -> dict:
    recipe = tomllib.loads((BUILT_IN_RECIPES / STUDY_RECIPE_FILE).read_text(encoding="utf-8"))
    return {**recipe, "steps": [expanded for step in recipe["steps"] for expanded in _expand_step(step, study)]}
