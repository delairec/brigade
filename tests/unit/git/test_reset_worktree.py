import unittest
from pathlib import Path

from brigade.git.reset_worktree import reset_worktree
from tests.unit.recording_process_runner import RecordingProcessRunner


class ResetWorktreeTest(unittest.TestCase):
    def test_should_put_the_branch_of_the_worktree_and_its_files_at_the_start(self):
        # Arrange
        git = RecordingProcessRunner()

        # Act
        reset_worktree(git, Path("/srv/worktrees/integration-dashboard"), "origin/integration/dashboard")

        # Assert
        self.assertEqual(
            git.commands,
            [
                (
                    "/srv/worktrees/integration-dashboard",
                    ("git", "reset", "--quiet", "--hard", "origin/integration/dashboard"),
                )
            ],
        )
