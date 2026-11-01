import unittest
from pathlib import Path

from brigade.git.add_branch_worktree import BranchWorktree
from brigade.git.switch_worktree_to_branch import switch_worktree_to_branch
from tests.unit.recording_process_runner import RecordingProcessRunner


class SwitchWorktreeToBranchTest(unittest.TestCase):
    def test_should_switch_the_worktree_to_the_existing_branch(self):
        # Arrange
        git = RecordingProcessRunner()
        worktree = BranchWorktree(
            path=Path("/srv/shop/.brigade/worktrees/B1"), branch="task/w1/B1", start="integration/w1"
        )

        # Act
        switch_worktree_to_branch(git, worktree)

        # Assert
        self.assertEqual(
            git.commands, [("/srv/shop/.brigade/worktrees/B1", ("git", "switch", "--quiet", "task/w1/B1"))]
        )
