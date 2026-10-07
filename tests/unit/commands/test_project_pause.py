import unittest

from brigade.commands.project_pause import COMMAND


class ProjectPauseTextTest(unittest.TestCase):
    def test_should_name_the_project_it_paused(self):
        # Arrange
        document = {"schema_version": 1, "project": "app", "status": "paused", "changed": True}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, "paused @PROJECT.app")
