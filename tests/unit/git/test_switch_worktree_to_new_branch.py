import unittest
from pathlib import Path

from brigade.git.add_branch_worktree import BranchWorktree
from brigade.git.switch_worktree_to_new_branch import switch_worktree_to_new_branch
from tests.unit.recording_process_runner import RecordingProcessRunner


class SwitchWorktreeToNewBranchTest(unittest.TestCase):
    def test_should_switch_the_worktree_to_a_branch_cut_from_its_start(self):
        # Arrange
        git = RecordingProcessRunner()
        worktree = BranchWorktree(
            path=Path("/srv/shop/.brigade/worktrees/B1"), branch="task/w1/B1", start="integration/w1"
        )

        # Act
        switch_worktree_to_new_branch(git, worktree)

        # Assert
        self.assertEqual(
            git.commands,
            [
                (
                    "/srv/shop/.brigade/worktrees/B1",
                    ("git", "switch", "--quiet", "--create", "task/w1/B1", "integration/w1"),
                )
            ],
        )
