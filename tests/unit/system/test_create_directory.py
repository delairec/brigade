import os
import tempfile
import unittest
from pathlib import Path

from brigade.errors import CannotWrite
from brigade.system.create_directory import create_directory


class CreateDirectory(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.path = Path(self.root.name) / "runs" / "20261006T120000Z-b57000"

    def test_should_create_the_directory_and_its_parents(self):
        # Act
        create_directory(self.path)

        # Assert
        self.assertTrue(self.path.is_dir())

    def test_should_keep_what_an_existing_directory_holds(self):
        # Arrange
        self.path.mkdir(parents=True)
        (self.path / "pid").write_text("42\n")

        # Act
        create_directory(self.path)

        # Assert
        self.assertEqual((self.path / "pid").read_text(), "42\n")

    def test_should_name_the_file_standing_where_the_directory_goes(self):
        # Arrange
        self.path.parent.mkdir()
        self.path.write_text("")

        # Act
        with self.assertRaises(CannotWrite) as refusal:
            create_directory(self.path)

        # Assert
        self.assertEqual(str(refusal.exception), f"cannot write {self.path}: File exists")


@unittest.skipIf(os.geteuid() == 0, "root writes where the permissions refuse it")
class CreateDirectoryWhereTheMachineRefusesTheWrite(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.machine = Path(self.root.name) / "machine"
        self.machine.mkdir()
        self.addCleanup(self.machine.chmod, 0o700)

    def test_should_name_the_first_directory_it_cannot_create(self):
        # Arrange
        self.machine.chmod(0o500)

        # Act
        with self.assertRaises(CannotWrite) as refusal:
            create_directory(self.machine / "runs" / "20261006T120000Z-b57000")

        # Assert
        self.assertEqual(str(refusal.exception), f"cannot write {self.machine / 'runs'}: Permission denied")
