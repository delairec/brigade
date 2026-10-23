import tempfile
import unittest
from pathlib import Path

from brigade.errors import CannotWrite
from brigade.system.delete_path import delete_path


class DeletePathTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.removed = Path(self.root.name) / "runs-removed"
        self.removed.mkdir()

    def test_should_delete_a_directory_and_what_it_holds(self):
        # Arrange
        run = self.removed / "20261006T120000Z-b57000"
        run.mkdir()
        (run / "run.json").write_text("{}\n")

        # Act
        delete_path(run)

        # Assert
        self.assertEqual(list(self.removed.iterdir()), [])

    def test_should_delete_a_file(self):
        # Arrange
        stray = self.removed / "stray.txt"
        stray.write_text("left over\n")

        # Act
        delete_path(stray)

        # Assert
        self.assertEqual(list(self.removed.iterdir()), [])

    def test_should_name_a_path_that_is_not_there(self):
        # Arrange
        missing = self.removed / "20261006T120000Z-b57000"

        # Act
        with self.assertRaises(CannotWrite) as refusal:
            delete_path(missing)

        # Assert
        self.assertEqual(str(refusal.exception), f"cannot write {missing}: No such file or directory")
