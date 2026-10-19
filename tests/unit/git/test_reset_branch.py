import unittest
from pathlib import Path

from brigade.git.reset_branch import reset_branch
from tests.unit.recording_process_runner import RecordingProcessRunner


class ResetBranchTest(unittest.TestCase):
    def test_should_switch_the_worktree_to_the_branch_created_anew_at_head(self):
        # Arrange
        git = RecordingProcessRunner()

        # Act
        reset_branch(git, Path("/srv/worktrees/b42"), "feat/b42")

        # Assert
        self.assertEqual(
            git.commands, [("/srv/worktrees/b42", ("git", "switch", "--quiet", "--force-create", "feat/b42"))]
        )
