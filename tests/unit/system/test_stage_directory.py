import errno
import tempfile
import unittest
from pathlib import Path

from brigade.errors import CannotWrite
from brigade.system.stage_directory import stage_directory


class StageDirectoryTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.tree = Path(self.root.name) / "refs" / "shop" / "abc123"
        self.tree.parent.mkdir(parents=True)

    def test_should_stage_a_hidden_directory_beside_the_tree(self):
        # Act
        with stage_directory(self.tree) as staging:
            staged = staging

        # Assert
        self.assertEqual(staged.parent, self.tree.parent)
        self.assertRegex(staged.name, r"^\.")

    def test_should_remove_the_staging_and_what_it_holds_on_leaving(self):
        # Arrange
        with stage_directory(self.tree) as staging:
            (staging / "tree").mkdir()

        # Act
        remaining = list(self.tree.parent.iterdir())

        # Assert
        self.assertEqual(remaining, [])

    def test_should_name_the_tree_when_the_staging_cannot_be_written(self):
        # Act
        with self.assertRaises(CannotWrite) as refusal, stage_directory(self.tree):
            raise NotADirectoryError(errno.ENOTDIR, "Not a directory", "/elsewhere/a/b")

        # Assert
        self.assertEqual(str(refusal.exception), f"cannot write {self.tree}: Not a directory")

    def test_should_name_the_tree_when_its_parent_cannot_hold_the_staging(self):
        # Arrange
        tree_under_a_file = self.tree / "file" / "abc123"
        self.tree.write_text("not a directory")

        # Act
        with self.assertRaises(CannotWrite) as refusal, stage_directory(tree_under_a_file):
            pass

        # Assert
        self.assertEqual(str(refusal.exception), f"cannot write {tree_under_a_file}: Not a directory")
