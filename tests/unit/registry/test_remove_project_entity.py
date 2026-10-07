import unittest

from brigade.registry.remove_project_entity import remove_project_entity


class RemoveProjectEntityTest(unittest.TestCase):
    def test_should_remove_the_block_of_the_project(self):
        # Arrange
        text = 'PROJECT alpha\n\tPATH "/srv/alpha"\n\nPROJECT beta\n\tPATH "/srv/beta"\n'

        # Act
        result = remove_project_entity(text, "alpha")

        # Assert
        self.assertEqual(result, 'PROJECT beta\n\tPATH "/srv/beta"\n')

    def test_should_return_the_text_unchanged_when_the_project_is_absent(self):
        # Arrange
        text = 'PROJECT alpha\n\tPATH "/srv/alpha"\n'

        # Act
        result = remove_project_entity(text, "gamma")

        # Assert
        self.assertEqual(result, text)
