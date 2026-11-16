import unittest

from brigade.corpus.shipped_data import SHIPPED_PROJECT_SCHEMA


class ShippedDataTest(unittest.TestCase):
    def test_should_declare_the_recipe_entity_in_the_schema_brigade_installs_in_a_project(self):
        # Act
        lines = SHIPPED_PROJECT_SCHEMA.read_text(encoding="utf-8").splitlines()

        # Assert
        self.assertIn("SCHEMA RECIPE", lines)
