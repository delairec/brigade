import unittest
from pathlib import Path

from brigade.git.remove_worktree import remove_worktree
from tests.unit.recording_process_runner import RecordingProcessRunner


class RemoveWorktreeTest(unittest.TestCase):
    def test_should_remove_the_worktree_even_with_changes(self):
        # Arrange
        git = RecordingProcessRunner()

        # Act
        remove_worktree(git, Path("/srv/shop"), Path("/srv/worktrees/b42"))

        # Assert
        self.assertEqual(git.commands, [("/srv/shop", ("git", "worktree", "remove", "--force", "/srv/worktrees/b42"))])
