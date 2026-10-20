import unittest

from brigade.corpus.read_entities import Entity, EntityField
from brigade.registry.is_on_github import is_on_github


class IsOnGithubTest(unittest.TestCase):
    def test_should_tell_whether_the_forge_of_the_project_is_github(self):
        for forge, expected in [("github", True), ("none", False)]:
            with self.subTest(forge=forge):
                # Arrange
                project = Entity(name="shop", fields=(EntityField(name="FORGE", value=forge),))

                # Act
                on_github = is_on_github(project)

                # Assert
                self.assertEqual(on_github, expected)
