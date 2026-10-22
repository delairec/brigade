import unittest
from pathlib import Path

from brigade.git.add_branch_worktree import BranchWorktree
from brigade.git.add_worktree_on_branch import add_worktree_on_branch
from tests.unit.recording_process_runner import RecordingProcessRunner


class AddWorktreeOnBranchTest(unittest.TestCase):
    def test_should_check_the_existing_branch_out_in_a_new_worktree(self):
        # Arrange
        git = RecordingProcessRunner()
        worktree = BranchWorktree(path=Path("/srv/worktrees/b42"), branch="feat/b42", start="origin/main")

        # Act
        add_worktree_on_branch(git, Path("/srv/shop"), worktree)

        # Assert
        self.assertEqual(
            git.commands, [("/srv/shop", ("git", "worktree", "add", "--quiet", "/srv/worktrees/b42", "feat/b42"))]
        )
