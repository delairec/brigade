import json
import tempfile
import unittest
from pathlib import Path

from brigade.recipes.list_recipes import list_recipes
from brigade.recipes.recipe_found import RecipeFound
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


def create_machine_recipe(name: str) -> RecipeFound:
    return RecipeFound(
        name=name,
        source="machine",
        document={
            "schema_version": 1,
            "name": name,
            "description": f"the machine's {name}",
            "params": [],
            "max_wall": 5,
            "steps": [],
        },
    )


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
                ("awawa", "status", "--json", corpus): ProcessAnswer(
                    stdout=json.dumps(
                        {
                            "entities": [
                                {"type": "DECISION", "name": "RecipesAreReviewed"},
                                {"type": "RECIPE", "name": "review"},
                            ]
                        }
                    )
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

    def test_should_read_no_recipe_from_a_corpus_that_does_not_declare_the_recipe_entity(self):
        # Arrange
        corpus = str(self.project)
        runner = RecordingProcessRunner(
            {
                ("awawa", "status", "--json", corpus): ProcessAnswer(
                    stdout=json.dumps({"entities": [{"type": "DECISION", "name": "RecipesAreReviewed"}]})
                ),
                ("awawa", "status", "RECIPE", "--json", corpus): ProcessAnswer(
                    exit_code=2, stderr="awawa status: `RECIPE` is not an entity type in this workspace\n"
                ),
            }
        )
        write_recipe(self.machine, "nightly", "the machine's nightly")
        places = RecipePlaces(self.project, self.project / ".brigade" / "recipes", self.machine, self.built_ins)

        # Act
        recipes = list_recipes(places, runner)

        # Assert
        self.assertEqual(recipes, (create_machine_recipe("nightly"),))

    def test_should_list_the_recipes_of_one_place_in_the_order_of_their_names(self):
        # Arrange
        for name in ("triage", "nightly", "review", "audit", "release"):
            write_recipe(self.machine, name, f"the machine's {name}")
        places = RecipePlaces(NO_CORPUS, self.project / ".brigade" / "recipes", self.machine, self.built_ins)

        # Act
        recipes = list_recipes(places, refuse_to_run)

        # Assert
        self.assertEqual(
            recipes,
            (
                create_machine_recipe("audit"),
                create_machine_recipe("nightly"),
                create_machine_recipe("release"),
                create_machine_recipe("review"),
                create_machine_recipe("triage"),
            ),
        )
