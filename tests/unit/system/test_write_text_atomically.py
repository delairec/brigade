import tempfile
import unittest
from pathlib import Path

from brigade.system.write_text_atomically import write_text_atomically
from tests.list_entry_names import list_entry_names

UNENCODABLE_TEXT = "\udc80"


class WriteTextAtomicallyTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.state = Path(self.root.name) / "state"
        self.path = self.state / "pid"

    def test_should_create_the_directory_and_write_the_text(self):
        # Act
        write_text_atomically(self.path, "4242\n")

        # Assert
        self.assertEqual(self.path.read_text(encoding="utf-8"), "4242\n")

    def test_should_replace_the_previous_text(self):
        # Arrange
        write_text_atomically(self.path, "4242\n")

        # Act
        write_text_atomically(self.path, "4343\n")

        # Assert
        self.assertEqual(self.path.read_text(encoding="utf-8"), "4343\n")

    def test_should_keep_the_previous_text_whole_when_the_new_one_cannot_be_written(self):
        # Arrange
        write_text_atomically(self.path, "4242\n")

        # Act
        with self.assertRaises(UnicodeEncodeError):
            write_text_atomically(self.path, UNENCODABLE_TEXT)

        # Assert
        self.assertEqual(self.path.read_text(encoding="utf-8"), "4242\n")
        self.assertEqual(list_entry_names(self.state), ["pid"])
