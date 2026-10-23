import tempfile
import unittest
from pathlib import Path

from brigade.git.delete_branch import delete_branch
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


class DeleteBranchTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.repository = Path(self.root.name) / "repository"
        self.repository.mkdir()
        run_git(self.repository, "init", "--quiet", "--initial-branch=main")
        run_git(self.repository, *IDENTITY, "commit", "--quiet", "--allow-empty", "-m", "first")

    def tearDown(self):
        self.root.cleanup()

    def test_should_delete_a_branch_merged_nowhere(self):
        # Arrange
        run_git(self.repository, "switch", "--quiet", "-c", "task/M1-empty-cart/S3")
        run_git(self.repository, *IDENTITY, "commit", "--quiet", "--allow-empty", "-m", "unmerged")
        run_git(self.repository, "switch", "--quiet", "main")

        # Act
        delete_branch(run_process_without_trail, self.repository, "task/M1-empty-cart/S3")

        # Assert
        self.assertEqual(run_git(self.repository, "branch", "--list", "task/M1-empty-cart/S3"), "")
