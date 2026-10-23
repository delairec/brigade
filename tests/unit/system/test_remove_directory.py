import tempfile
import unittest
from pathlib import Path

from brigade.errors import CannotWrite
from brigade.system.remove_directory import remove_directory

LONGEST_NAME = 255


class RemoveDirectoryTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.parent = Path(self.root.name) / "refs" / "shop"
        self.parent.mkdir(parents=True)

    def test_should_remove_the_directory_and_what_it_holds(self):
        # Arrange
        tree = self.parent / "abc123"
        (tree / "docs").mkdir(parents=True)
        (tree / "docs" / "README.md").write_text("cached\n")

        # Act
        remove_directory(tree)

        # Assert
        self.assertEqual(list(self.parent.iterdir()), [])

    def test_should_name_a_directory_whose_name_leaves_no_room_to_set_it_aside(self):
        # Arrange
        tree = self.parent / ("a" * LONGEST_NAME)
        tree.mkdir()

        # Act
        with self.assertRaises(CannotWrite) as refusal:
            remove_directory(tree)

        # Assert
        self.assertEqual(str(refusal.exception), f"cannot write {tree}: File name too long")
