import json
import os
import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
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

    def test_should_name_the_target_it_cannot_replace_and_leave_no_temporary_file(self):
        # Arrange
        self.path.mkdir(parents=True)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            write_json_atomically(self.path, {"schema_version": 1, "actions_applied": 0})

        # Assert
        self.assertEqual(
            (str(refusal.exception), [path.name for path in self.state.iterdir()]),
            (f"cannot write {self.path}: Is a directory", ["tick.json"]),
        )


@unittest.skipIf(os.geteuid() == 0, "root writes where the permissions refuse it")
class WriteJsonAtomicallyWhereTheMachineRefusesTheWrite(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.machine = Path(self.root.name) / "machine"
        self.machine.mkdir()
        self.addCleanup(self.machine.chmod, 0o700)
        self.state = self.machine / "state"
        self.path = self.state / "tick.json"

    def test_should_name_the_directory_it_cannot_create(self):
        # Arrange
        self.machine.chmod(0o500)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            write_json_atomically(self.path, {"schema_version": 1, "actions_applied": 0})

        # Assert
        self.assertEqual(str(refusal.exception), f"cannot write {self.state}: Permission denied")

    def test_should_name_the_target_of_the_temporary_file_it_cannot_create(self):
        # Arrange
        self.state.mkdir()
        self.state.chmod(0o500)
        self.addCleanup(self.state.chmod, 0o700)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            write_json_atomically(self.path, {"schema_version": 1, "actions_applied": 0})

        # Assert
        self.assertEqual(str(refusal.exception), f"cannot write {self.path}: Permission denied")
