import tempfile
import unittest
from pathlib import Path

from brigade.errors import CannotWrite
from brigade.system.write_bytes_file import write_bytes_file


class WriteBytesFileTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.path = Path(self.root.name) / "config.toml"

    def test_should_write_the_bytes(self):
        # Act
        write_bytes_file(self.path, b"[clients]\n")

        # Assert
        self.assertEqual(self.path.read_bytes(), b"[clients]\n")

    def test_should_name_the_file_it_cannot_create_where_a_file_stands_for_its_directory(self):
        # Arrange
        self.path.parent.joinpath("brigade").touch()
        nested = self.path.parent / "brigade" / "config.toml"

        # Act
        with self.assertRaises(CannotWrite) as refusal:
            write_bytes_file(nested, b"[clients]\n")

        # Assert
        self.assertEqual(str(refusal.exception), f"cannot write {nested}: Not a directory")
