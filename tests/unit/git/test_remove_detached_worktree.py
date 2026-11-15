import unittest
from pathlib import Path

from brigade.git.add_detached_worktree import DetachedWorktree
from brigade.git.remove_detached_worktree import remove_detached_worktree
from tests.unit.recording_process_runner import RecordingProcessRunner


class RemoveDetachedWorktreeTest(unittest.TestCase):
    def test_should_remove_the_worktree_its_command_locked_even_with_changes(self):
        # Arrange
        git = RecordingProcessRunner()
        worktree = DetachedWorktree(
            repository=Path("/srv/shop"), path=Path("/srv/worktrees/review"), start="4f2a9c1", reason="brigade run"
        )

        # Act
        remove_detached_worktree(git, worktree)

        # Assert
        self.assertEqual(
            git.commands, [("/srv/shop", ("git", "worktree", "remove", "--force", "--force", "/srv/worktrees/review"))]
        )
