import json
from pathlib import Path

from tests.unit.recording_process_runner import ProcessAnswer

RECIPE_TYPE = "RECIPE"


def _describe_step(argv: tuple[str, ...]) -> dict:
    return {
        "name": "STEP",
        "atoms": ["command"],
        "fields": [{"name": "ARGV", "atoms": [json.dumps(argument)], "fields": []} for argument in argv],
    }


def _describe_recipe(name: str, argvs: tuple[tuple[str, ...], ...]) -> dict:
    return {
        "type": RECIPE_TYPE,
        "name": name,
        "fields": [
            {"name": "DESC", "atoms": [json.dumps(f"the {name} of the project")], "fields": []},
            {"name": "SCHEMA_VERSION", "atoms": ["1"], "fields": []},
            {"name": "MAX_WALL", "atoms": ["30"], "fields": []},
            *(_describe_step(argv) for argv in argvs),
        ],
    }


def create_recipe_answers(corpus: Path, recipes: dict[str, tuple[tuple[str, ...], ...]]) -> dict:
    listed = {"entities": [{"type": RECIPE_TYPE, "name": name} for name in recipes]}
    return {
        ("awawa", "status", "--json", str(corpus)): ProcessAnswer(stdout=json.dumps(listed)),
        **{
            ("awawa", "show", f"@{RECIPE_TYPE}.{name}", "--json", str(corpus)): ProcessAnswer(
                stdout=json.dumps(_describe_recipe(name, argvs))
            )
            for name, argvs in recipes.items()
        },
    }
