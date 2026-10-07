import unittest

from brigade.registry.set_project_status import set_project_status

REGISTRY = 'PROJECT shop\n\tPATH "/srv/shop"\n\tSTATUS active\n'


class SetProjectStatusTest(unittest.TestCase):
    def test_should_answer_nothing_when_the_text_does_not_write_the_project(self):
        # Act
        text = set_project_status(REGISTRY, "ghost", "paused")

        # Assert
        self.assertIsNone(text)
