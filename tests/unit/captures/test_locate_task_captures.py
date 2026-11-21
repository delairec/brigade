import unittest
from pathlib import Path

from brigade.captures.locate_task_captures import locate_task_captures
from tests.unit.create_test_paths import create_test_paths


class LocateTaskCapturesTest(unittest.TestCase):
    def test_should_keep_the_captures_of_a_task_under_the_state_directory_by_project_and_task(self):
        # Arrange
        paths = create_test_paths(Path("/home/sailor"))

        # Act
        directory = locate_task_captures(paths, "harbour", "T7")

        # Assert
        self.assertEqual(directory, paths.state_root / "captures" / "harbour" / "T7")
