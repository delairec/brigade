from pathlib import Path

from brigade.git.cut_branch import BranchCut, cut_branch
from tests.integration.repository_test_case import IDENTITY, RepositoryTestCase
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


class CutBranchTest(RepositoryTestCase):
    def test_should_create_the_branch_at_its_start_leaving_the_checkout_on_its_branch(self):
        # Arrange
        run_git(self.repository, "branch", "release")
        run_git(self.repository, *IDENTITY, "commit", "--quiet", "--allow-empty", "-m", "second")

        # Act
        cut_branch(
            run_process_without_trail,
            BranchCut(repository=self.repository, branch="integration/shop_w1", start="release"),
        )

        # Assert
        self.assertEqual(
            run_git(self.repository, "rev-parse", "integration/shop_w1"),
            run_git(self.repository, "rev-parse", "release"),
        )
        self.assertEqual(run_git(self.repository, "branch", "--show-current"), "main\n")
