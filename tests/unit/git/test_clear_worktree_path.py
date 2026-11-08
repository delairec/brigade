import tempfile
import unittest
from pathlib import Path

from brigade.git.clear_worktree_path import clear_worktree_path
from tests.unit.recording_process_runner import RecordingProcessRunner


class ClearWorktreePathTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.worktree = Path(directory.name) / "checkout"

    def test_should_delete_what_a_former_attempt_left_at_the_path(self):
        # Arrange
        self.worktree.mkdir()
        (self.worktree / "half-written.md").write_text("left by the attempt\n", encoding="utf-8")

        # Act
        clear_worktree_path(RecordingProcessRunner(), Path("/srv/oak"), self.worktree)

        # Assert
        self.assertFalse(self.worktree.exists())

    def test_should_prune_the_registration_of_a_path_nothing_occupies(self):
        # Arrange
        git = RecordingProcessRunner()

        # Act
        clear_worktree_path(git, Path("/srv/oak"), self.worktree)

        # Assert
        self.assertEqual(git.commands, [("/srv/oak", ("git", "worktree", "prune"))])
