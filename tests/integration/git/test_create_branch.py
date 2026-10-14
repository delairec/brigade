import tempfile
import unittest
from pathlib import Path

from brigade.git.create_branch import create_branch
from tests.integration.run_process_without_trail import run_process_without_trail
from tests.process_launcher import ProcessLauncher

IDENTITY = ("-c", "user.name=Ada Lovelace", "-c", "user.email=ada@example.org")


def run_git(repository: Path, *arguments: str) -> str:
    completed = ProcessLauncher.run(
        ["git", "-C", str(repository), *arguments],
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout


class RepositoryTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.repository = Path(self.root.name) / "repository"
        self.repository.mkdir()
        run_git(self.repository, "init", "--quiet", "--initial-branch=main")
        run_git(self.repository, *IDENTITY, "commit", "--quiet", "--allow-empty", "-m", "first")

    def tearDown(self):
        self.root.cleanup()


class CreateBranchTest(RepositoryTestCase):
    def test_should_check_out_a_new_branch_at_the_commit_of_the_worktree(self):
        # Arrange
        run_git(self.repository, "switch", "--quiet", "--detach")

        # Act
        create_branch(run_process_without_trail, self.repository, "integration/W1-empty-the-cart")

        # Assert
        self.assertEqual(run_git(self.repository, "branch", "--show-current"), "integration/W1-empty-the-cart\n")
        self.assertEqual(
            run_git(self.repository, "rev-parse", "integration/W1-empty-the-cart"),
            run_git(self.repository, "rev-parse", "main"),
        )
