import unittest
from pathlib import Path

from brigade.corpus.read_entities import Entity, EntityField
from brigade.recipes.locate_recipes import locate_recipes
from brigade.recipes.recipe_places import BUILT_IN_RECIPES, RecipePlaces
from tests.unit.create_test_paths import create_test_paths

PROJECT = Path("/srv/shop")
UNREGISTERED = None


class LocateRecipesTest(unittest.TestCase):
    def test_should_read_the_recipes_of_a_project_from_its_corpus_when_it_has_one(self):
        # Arrange
        rows = (
            ("a project in control", Entity("shop", (EntityField("PATH", "/srv/shop"),)), Path("/srv/shop")),
            (
                "a project in area",
                Entity("shop", (EntityField("MODE", "area"), EntityField("CORPUS", "brigade"))),
                Path("/srv/shop/brigade"),
            ),
            ("a project in none", Entity("shop", (EntityField("MODE", "none"),)), None),
            ("a project no registry names", UNREGISTERED, None),
        )
        for title, entity, corpus in rows:
            with self.subTest(title):
                # Act
                places = locate_recipes(PROJECT, entity, create_test_paths(Path("/srv/machine")))

                # Assert
                self.assertEqual(places.project_corpus, corpus)

    def test_should_place_the_recipe_files_of_the_project_the_machine_and_brigade(self):
        # Act
        places = locate_recipes(PROJECT, UNREGISTERED, create_test_paths(Path("/srv/machine")))

        # Assert
        self.assertEqual(
            places,
            RecipePlaces(
                project_corpus=None,
                project_directory=Path("/srv/shop/.brigade/recipes"),
                machine_directory=Path("/srv/machine/config/recipes"),
                built_ins=BUILT_IN_RECIPES,
            ),
        )
