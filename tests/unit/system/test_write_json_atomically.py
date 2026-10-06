import json
import tempfile
import unittest
from pathlib import Path

from brigade.system.write_json_atomically import write_json_atomically


class WriteJsonAtomically(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.state = Path(self.root.name) / "state"
        self.path = self.state / "tick.json"

    def tearDown(self):
        self.root.cleanup()

    def test_should_create_the_directory_and_write_the_document(self):
        # Act
        write_json_atomically(self.path, {"schema_version": 1, "actions_applied": 0})

        # Assert
        self.assertEqual(json.loads(self.path.read_text()), {"schema_version": 1, "actions_applied": 0})

    def test_should_replace_the_previous_document(self):
        # Arrange
        write_json_atomically(self.path, {"schema_version": 1, "actions_applied": 0})

        # Act
        write_json_atomically(self.path, {"schema_version": 1, "actions_applied": 3})

        # Assert
        self.assertEqual(json.loads(self.path.read_text()), {"schema_version": 1, "actions_applied": 3})

    def test_should_leave_no_temporary_file_beside_it(self):
        # Act
        write_json_atomically(self.path, {"schema_version": 1, "actions_applied": 0})

        # Assert
        self.assertEqual([path.name for path in self.state.iterdir()], ["tick.json"])
