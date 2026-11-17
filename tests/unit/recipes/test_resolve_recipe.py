import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.recipes.recipe_found import RecipeFound
from brigade.recipes.recipe_places import RecipePlaces
from brigade.recipes.resolve_recipe import resolve_recipe
from tests.unit.recipes.recipe_files import write_recipe
from tests.unit.refuse_to_run import refuse_to_run

NO_CORPUS = None


class ResolveRecipeTest(unittest.TestCase):
    def setUp(self):
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        self.root = Path(root.name)
        self.places = RecipePlaces(
            NO_CORPUS, self.root / "shop" / ".brigade" / "recipes", self.root / "config" / "recipes", self.root / "data"
        )

    def test_should_resolve_a_recipe_from_the_first_of_its_three_places_holding_it(self):
        # Arrange
        write_recipe(self.places.machine_directory, "review", "the machine's review")
        write_recipe(self.places.built_ins, "review", "the built-in review")

        # Act
        recipe = resolve_recipe("review", self.places, refuse_to_run)

        # Assert
        self.assertEqual(
            recipe,
            RecipeFound(
                name="review",
                source="machine",
                document={
                    "schema_version": 1,
                    "name": "review",
                    "description": "the machine's review",
                    "params": [],
                    "max_wall": 5,
                    "steps": [],
                },
            ),
        )

    def test_should_resolve_the_recipe_named_among_the_recipes_of_its_place(self):
        # Arrange
        write_recipe(self.places.machine_directory, "nightly", "the machine's nightly")
        write_recipe(self.places.machine_directory, "review", "the machine's review")

        # Act
        recipe = resolve_recipe("review", self.places, refuse_to_run)

        # Assert
        self.assertEqual(
            recipe,
            RecipeFound(
                name="review",
                source="machine",
                document={
                    "schema_version": 1,
                    "name": "review",
                    "description": "the machine's review",
                    "params": [],
                    "max_wall": 5,
                    "steps": [],
                },
            ),
        )

    def test_should_refuse_a_name_no_place_holds_naming_it(self):
        # Act
        with self.assertRaises(BrigadeError) as raised:
            resolve_recipe("review", self.places, refuse_to_run)

        # Assert
        self.assertEqual(
            str(raised.exception),
            f"no recipe review: not in the project, in {self.root}/config/recipes or built in",
        )
