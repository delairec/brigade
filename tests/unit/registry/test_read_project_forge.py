import unittest

from brigade.corpus.read_entities import Entity, EntityField
from brigade.registry.read_project_forge import read_project_forge


class ReadProjectForgeTest(unittest.TestCase):
    def test_should_read_the_forge_the_project_names(self):
        for forge in ["github", "none"]:
            with self.subTest(forge=forge):
                # Arrange
                project = Entity(name="shop", fields=(EntityField(name="FORGE", value=forge),))

                # Act
                read = read_project_forge(project)

                # Assert
                self.assertEqual(read, forge)

    def test_should_read_none_from_a_project_naming_no_forge(self):
        # Arrange
        project_without_forge_field = Entity(name="shop", fields=())

        # Act
        read = read_project_forge(project_without_forge_field)

        # Assert
        self.assertEqual(read, "none")
