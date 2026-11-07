import json
import tempfile
import unittest
from pathlib import Path

from brigade.tick.head_proof import TaskCheck
from brigade.tick.read_task_check import read_task_check


class ReadTaskCheckTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.state_root = Path(directory.name)

    def test_should_read_the_head_the_task_was_checked_at_and_its_failed_commands(self):
        # Arrange
        record = self.state_root / "checks" / "oak" / "B7.json"
        record.parent.mkdir(parents=True)
        record.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "project": "oak",
                    "task": "B7",
                    "head": "c0ffee",
                    "checks": [{"command": "npm test", "passed": False}, {"command": "privacy", "passed": True}],
                }
            ),
            encoding="utf-8",
        )

        # Act
        task_check = read_task_check(self.state_root, "oak", "B7")

        # Assert
        self.assertEqual(task_check, TaskCheck(head="c0ffee", failed_commands=("npm test",)))

    def test_should_find_no_check_of_a_task_never_checked(self):
        # Act
        task_check = read_task_check(self.state_root, "oak", "B7")

        # Assert
        self.assertIsNone(task_check)
