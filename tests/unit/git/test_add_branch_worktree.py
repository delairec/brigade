import unittest
from pathlib import Path

from brigade.git.add_branch_worktree import BranchWorktree, add_branch_worktree
from tests.unit.recording_process_runner import RecordingProcessRunner


class AddBranchWorktreeTest(unittest.TestCase):
    def test_should_create_the_branch_in_a_new_worktree_from_its_start(self):
        # Arrange
        git = RecordingProcessRunner()
        worktree = BranchWorktree(path=Path("/srv/worktrees/b42"), branch="feat/b42", start="origin/main")

        # Act
        add_branch_worktree(git, Path("/srv/shop"), worktree)

        # Assert
        self.assertEqual(
            git.commands,
            [
                (
                    "/srv/shop",
                    ("git", "worktree", "add", "--quiet", "-b", "feat/b42", "/srv/worktrees/b42", "origin/main"),
                )
            ],
        )
