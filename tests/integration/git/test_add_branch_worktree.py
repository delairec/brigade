import tempfile
import unittest
from pathlib import Path

from brigade.git.add_branch_worktree import BranchWorktree, add_branch_worktree
from tests.integration.repository_test_case import IDENTITY
from tests.integration.run_process_without_trail import run_process_without_trail
from tests.process_launcher import ProcessLauncher


def run_git(repository: Path, *arguments: str) -> str:
    completed = ProcessLauncher.run(
        ["git", "-C", str(repository), *arguments],
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout


class AddBranchWorktreeTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.repository = Path(self.root.name) / "repository"
        self.repository.mkdir()
        run_git(self.repository, "init", "--quiet", "--initial-branch=main")
        run_git(self.repository, *IDENTITY, "commit", "--quiet", "--allow-empty", "-m", "first")
        run_git(self.repository, "branch", "integration/M1-empty-cart")
        run_git(self.repository, *IDENTITY, "commit", "--quiet", "--allow-empty", "-m", "second")

    def tearDown(self):
        self.root.cleanup()

    def test_should_check_out_a_new_branch_cut_from_the_start_in_the_worktree(self):
        # Arrange
        worktree = BranchWorktree(
            path=Path(self.root.name) / "worktrees" / "S3",
            branch="task/M1-empty-cart/S3",
            start="integration/M1-empty-cart",
        )

        # Act
        add_branch_worktree(run_process_without_trail, self.repository, worktree)

        # Assert
        self.assertEqual(run_git(worktree.path, "branch", "--show-current"), "task/M1-empty-cart/S3\n")
        self.assertEqual(run_git(worktree.path, "log", "--format=%s"), "first\n")
