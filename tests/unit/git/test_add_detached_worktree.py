import unittest
from pathlib import Path

from brigade.git.add_detached_worktree import add_detached_worktree
from tests.unit.recording_process_runner import RecordingProcessRunner


class AddDetachedWorktreeTest(unittest.TestCase):
    def test_should_check_out_the_start_detached_in_a_new_worktree(self):
        # Arrange
        git = RecordingProcessRunner()

        # Act
        add_detached_worktree(git, Path("/srv/shop"), Path("/srv/worktrees/review"), "4f2a9c1")

        # Assert
        self.assertEqual(
            git.commands,
            [("/srv/shop", ("git", "worktree", "add", "--quiet", "--detach", "/srv/worktrees/review", "4f2a9c1"))],
        )
