import tempfile
import unittest
from pathlib import Path

from brigade.errors import ToolFailure
from brigade.git.require_ancestor import require_ancestor
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


class RequireAncestorTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.repository = Path(self.root.name) / "repository"
        self.repository.mkdir()
        run_git(self.repository, "init", "--quiet", "--initial-branch=main")
        run_git(self.repository, *IDENTITY, "commit", "--quiet", "--allow-empty", "-m", "first")
        run_git(self.repository, "branch", "integration/M1-empty-cart")

    def tearDown(self):
        self.root.cleanup()

    def test_should_accept_a_head_descending_from_the_ancestor(self):
        # Arrange
        run_git(self.repository, *IDENTITY, "commit", "--quiet", "--allow-empty", "-m", "second")

        # Act
        require_ancestor(run_process_without_trail, self.repository, "integration/M1-empty-cart")

        # Assert
        self.assertEqual(run_git(self.repository, "log", "--format=%s"), "second\nfirst\n")

    def test_should_fail_on_a_head_that_no_longer_descends_from_the_ancestor(self):
        # Arrange
        run_git(self.repository, "checkout", "--quiet", "--orphan", "elsewhere")
        run_git(self.repository, *IDENTITY, "commit", "--quiet", "--allow-empty", "-m", "elsewhere")

        # Act
        with self.assertRaises(ToolFailure):
            require_ancestor(run_process_without_trail, self.repository, "integration/M1-empty-cart")
