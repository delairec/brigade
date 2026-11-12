import unittest

from brigade.corpus.read_entities import Entity, EntityField
from brigade.registry.render_project_schema import render_project_schema


def create_project(*fields: EntityField) -> Entity:
    return Entity(name="app", fields=fields)


class RenderProjectSchemaTest(unittest.TestCase):
    def test_should_declare_impl_a_string_in_an_area(self):
        # Arrange
        project = create_project(EntityField(name="MODE", value="area"))

        # Act
        schema = render_project_schema(project)

        # Assert
        self.assertIn("\t\tFIELD IMPL string\n", schema)
        self.assertNotIn("FIELD IMPL anchor", schema)

    def test_should_keep_impl_an_anchor_outside_an_area(self):
        # Arrange
        project = create_project(EntityField(name="MODE", value="control"))

        # Act
        schema = render_project_schema(project)

        # Assert
        self.assertIn("\t\tFIELD IMPL anchor\n", schema)

    def test_should_keep_impl_an_anchor_for_a_project_naming_no_mode(self):
        # Arrange
        project_naming_no_mode = create_project()

        # Act
        schema = render_project_schema(project_naming_no_mode)

        # Assert
        self.assertIn("\t\tFIELD IMPL anchor\n", schema)
