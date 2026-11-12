import unittest

from brigade.corpus.read_entities import Entity, EntityField
from brigade.registry.is_on_a_forge import is_on_a_forge


class IsOnAForgeTest(unittest.TestCase):
    def test_should_tell_whether_the_project_acts_through_a_forge(self):
        for forge, expected in [("github", True), ("none", False)]:
            with self.subTest(forge=forge):
                # Arrange
                project = Entity(name="shop", fields=(EntityField(name="FORGE", value=forge),))

                # Act
                on_a_forge = is_on_a_forge(project)

                # Assert
                self.assertEqual(on_a_forge, expected)
