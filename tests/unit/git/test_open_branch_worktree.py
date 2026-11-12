import unittest
from pathlib import Path

from brigade.git.add_branch_worktree import BranchWorktree
from brigade.git.open_branch_worktree import open_branch_worktree
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

REPOSITORY = Path("/srv/shop")
WORKTREE = BranchWorktree(
    path=Path("/srv/shop/.brigade/worktrees/integration-cart"), branch="integration/cart", start="integration/cart"
)
LIST_WORKTREES = ("git", "worktree", "list", "--porcelain", "-z")
ADD_THE_WORKTREE = ("git", "worktree", "add", "--quiet", str(WORKTREE.path), "integration/cart")
RESET_THE_WORKTREE = ("git", "reset", "--quiet", "--hard", "integration/cart")


class OpenBranchWorktreeTest(unittest.TestCase):
    def test_should_add_a_worktree_on_the_branch_when_none_stands_and_put_it_on_its_start(self):
        # Arrange
        runner = RecordingProcessRunner({LIST_WORKTREES: ProcessAnswer(stdout="")})

        # Act
        open_branch_worktree(runner, REPOSITORY, WORKTREE)

        # Assert
        self.assertEqual(runner.list_argvs(), [LIST_WORKTREES, ADD_THE_WORKTREE, RESET_THE_WORKTREE])

    def test_should_only_put_on_its_start_the_worktree_already_standing_on_the_branch(self):
        # Arrange
        listing = f"worktree {WORKTREE.path}\0HEAD abc\0branch refs/heads/integration/cart\0\0"
        runner = RecordingProcessRunner({LIST_WORKTREES: ProcessAnswer(stdout=listing)})

        # Act
        open_branch_worktree(runner, REPOSITORY, WORKTREE)

        # Assert
        self.assertEqual(runner.list_argvs(), [LIST_WORKTREES, RESET_THE_WORKTREE])
