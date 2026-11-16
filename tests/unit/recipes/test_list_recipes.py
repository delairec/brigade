import json
import tempfile
import unittest
from pathlib import Path

from brigade.recipes.list_recipes import RecipeFound, list_recipes
from brigade.recipes.recipe_places import RecipePlaces
from tests.unit.recipes.recipe_entity import REVIEW_RECIPE_DOCUMENT, REVIEW_RECIPE_ENTITY, REVIEW_RECIPE_TOML
from tests.unit.recipes.recipe_files import write_recipe
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner
from tests.unit.refuse_to_run import refuse_to_run

NO_CORPUS = None


def create_document(description: str) -> dict:
    return {
        "schema_version": 1,
        "name": "review",
        "description": description,
        "params": [],
        "max_wall": 5,
        "steps": [],
    }


class ListRecipesTest(unittest.TestCase):
    def setUp(self):
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        self.root = Path(root.name)
        self.project = self.root / "shop"
        self.machine = self.root / "config" / "recipes"
        self.built_ins = self.root / "brigade" / "recipes" / "data"

    def test_should_list_the_recipes_of_the_project_then_the_machine_then_the_built_ins(self):
        # Arrange
        write_recipe(self.project / ".brigade" / "recipes", "review", "the project's review")
        write_recipe(self.machine, "review", "the machine's review")
        write_recipe(self.built_ins, "review", "the built-in review")
        places = RecipePlaces(NO_CORPUS, self.project / ".brigade" / "recipes", self.machine, self.built_ins)

        # Act
        recipes = list_recipes(places, refuse_to_run)

        # Assert
        self.assertEqual(
            recipes,
            (
                RecipeFound(name="review", source="project", document=create_document("the project's review")),
                RecipeFound(name="review", source="machine", document=create_document("the machine's review")),
                RecipeFound(name="review", source="built-in", document=create_document("the built-in review")),
            ),
        )

    def test_should_read_the_recipes_of_a_project_without_corpus_from_its_brigade_recipes(self):
        # Arrange
        recipes_directory = self.project / ".brigade" / "recipes"
        recipes_directory.mkdir(parents=True)
        (recipes_directory / "review.toml").write_text(REVIEW_RECIPE_TOML)
        (recipes_directory / "README.md").write_text("the recipes of the shop\n")
        places = RecipePlaces(NO_CORPUS, recipes_directory, self.machine, self.built_ins)

        # Act
        recipes = list_recipes(places, refuse_to_run)

        # Assert
        self.assertEqual(recipes, (RecipeFound(name="review", source="project", document=REVIEW_RECIPE_DOCUMENT),))

    def test_should_read_the_recipes_of_a_project_with_a_corpus_from_its_recipe_entities(self):
        # Arrange
        corpus = str(self.project)
        runner = RecordingProcessRunner(
            {
                ("awawa", "status", "RECIPE", "--json", corpus): ProcessAnswer(
                    stdout=json.dumps({"entities": [{"type": "RECIPE", "name": "review"}]})
                ),
                ("awawa", "show", "@RECIPE.review", "--json", corpus): ProcessAnswer(
                    stdout=json.dumps(REVIEW_RECIPE_ENTITY)
                ),
            }
        )
        write_recipe(self.project / ".brigade" / "recipes", "ignored", "a file the corpus replaces")
        places = RecipePlaces(self.project, self.project / ".brigade" / "recipes", self.machine, self.built_ins)

        # Act
        recipes = list_recipes(places, runner)

        # Assert
        self.assertEqual(recipes, (RecipeFound(name="review", source="project", document=REVIEW_RECIPE_DOCUMENT),))
