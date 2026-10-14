import tempfile
import unittest
from pathlib import Path

from brigade.git.find_branch import find_branch
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


class FindBranchTest(RepositoryTestCase):
    def test_should_find_a_branch_of_the_repository(self):
        # Arrange
        run_git(self.repository, "branch", "integration/W1-empty-the-cart")

        # Act
        found = find_branch(run_process_without_trail, self.repository, "integration/W1-empty-the-cart")

        # Assert
        self.assertTrue(found)

    def test_should_not_find_a_branch_the_repository_lacks(self):
        # Act
        found = find_branch(run_process_without_trail, self.repository, "integration/W1-empty-the-cart")

        # Assert
        self.assertFalse(found)
