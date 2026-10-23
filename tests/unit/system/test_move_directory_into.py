import tempfile
import unittest
from pathlib import Path

from brigade.errors import CannotWrite
from brigade.system.move_directory_into import move_directory_into


class MoveDirectoryIntoTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.run = Path(self.root.name) / "runs" / "20261006T120000Z-b57000"
        self.run.mkdir(parents=True)
        (self.run / "run.json").write_text("{}\n")
        self.destination = Path(self.root.name) / "runs-removed"

    def test_should_move_the_directory_under_its_name_into_a_destination_it_creates(self):
        # Act
        moved = move_directory_into(self.run, self.destination)

        # Assert
        self.assertEqual((moved / "run.json").read_text(), "{}\n")

    def test_should_answer_where_the_directory_now_stands(self):
        # Act
        moved = move_directory_into(self.run, self.destination)

        # Assert
        self.assertEqual(moved, Path(self.root.name) / "runs-removed" / "20261006T120000Z-b57000")

    def test_should_name_the_destination_a_file_holds(self):
        # Arrange
        self.destination.write_text("not a directory")

        # Act
        with self.assertRaises(CannotWrite) as refusal:
            move_directory_into(self.run, self.destination)

        # Assert
        self.assertEqual(str(refusal.exception), f"cannot write {self.destination}: File exists")

    def test_should_name_the_destination_when_the_move_fails(self):
        # Arrange
        (self.destination / "20261006T120000Z-b57000" / "kept").mkdir(parents=True)

        # Act
        with self.assertRaises(CannotWrite) as refusal:
            move_directory_into(self.run, self.destination)

        # Assert
        self.assertEqual(str(refusal.exception), f"cannot write {self.destination}: Directory not empty")
