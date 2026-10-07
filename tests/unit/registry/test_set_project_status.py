import unittest

from brigade.registry.set_project_status import set_project_status


class SetProjectStatusTest(unittest.TestCase):
    def test_should_replace_the_status_of_the_project(self):
        # Arrange
        text = 'PROJECT alpha\n\tSTATUS active\n\tPATH "/srv/alpha"\n'

        # Act
        result = set_project_status(text, "alpha", "paused")

        # Assert
        self.assertEqual(result, 'PROJECT alpha\n\tSTATUS paused\n\tPATH "/srv/alpha"\n')

    def test_should_return_none_when_the_project_is_absent(self):
        # Arrange
        text = "PROJECT alpha\n\tSTATUS active\n"

        # Act
        result = set_project_status(text, "gamma", "paused")

        # Assert
        self.assertIsNone(result)
