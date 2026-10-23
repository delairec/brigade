import tempfile
import unittest
from pathlib import Path

from brigade.errors import CannotWrite
from brigade.system.place_directory_atomically import place_directory_atomically


class PlaceDirectoryAtomicallyTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.staged = Path(self.root.name) / ".staging" / "tree"
        self.staged.mkdir(parents=True)
        (self.staged / "README.md").write_text("staged\n")
        self.place = Path(self.root.name) / "abc123"

    def test_should_move_the_staged_directory_into_its_place(self):
        # Act
        place_directory_atomically(self.staged, self.place)

        # Assert
        self.assertEqual((self.place / "README.md").read_text(), "staged\n")

    def test_should_keep_the_directory_another_placement_left_there(self):
        # Arrange
        self.place.mkdir()
        (self.place / "README.md").write_text("placed meanwhile\n")

        # Act
        place_directory_atomically(self.staged, self.place)

        # Assert
        self.assertEqual((self.place / "README.md").read_text(), "placed meanwhile\n")

    def test_should_name_the_place_a_file_holds(self):
        # Arrange
        self.place.write_text("not a tree")

        # Act
        with self.assertRaises(CannotWrite) as refusal:
            place_directory_atomically(self.staged, self.place)

        # Assert
        self.assertEqual(str(refusal.exception), f"cannot write {self.place}: Not a directory")
