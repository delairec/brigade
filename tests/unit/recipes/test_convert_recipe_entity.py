import tomllib
import unittest

from brigade.recipes.convert_recipe_entity import convert_recipe_entity
from tests.unit.recipes.recipe_entity import REVIEW_RECIPE_ENTITY, REVIEW_RECIPE_TOML


class ConvertRecipeEntityTest(unittest.TestCase):
    def test_should_resolve_a_recipe_entity_to_the_document_of_the_same_recipe_written_in_toml(self):
        # Arrange
        written_in_toml = tomllib.loads(REVIEW_RECIPE_TOML)

        # Act
        document = convert_recipe_entity(REVIEW_RECIPE_ENTITY)

        # Assert
        self.assertEqual(document, written_in_toml)
