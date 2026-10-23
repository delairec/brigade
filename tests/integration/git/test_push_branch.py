from pathlib import Path

from brigade.git.push_branch import BranchPush, push_branch
from tests.integration.repository_test_case import RepositoryTestCase
from tests.integration.run_process_without_trail import run_process_without_trail
from tests.process_launcher import ProcessLauncher

NO_ENVIRONMENT = {}


def run_git(repository: Path, *arguments: str) -> str:
    completed = ProcessLauncher.run(
        ["git", "-C", str(repository), *arguments],
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout


class PushBranchTest(RepositoryTestCase):
    def test_should_push_the_branch_to_the_origin_remote(self):
        # Arrange
        remote = Path(self.root.name) / "remote.git"
        run_git(self.repository, "init", "--quiet", "--bare", str(remote))
        run_git(self.repository, "remote", "add", "origin", str(remote))
        run_git(self.repository, "branch", "integration/W1-empty-the-cart")

        # Act
        push_branch(
            run_process_without_trail,
            BranchPush(repository=self.repository, branch="integration/W1-empty-the-cart", environment=NO_ENVIRONMENT),
        )

        # Assert
        self.assertEqual(
            run_git(remote, "rev-parse", "integration/W1-empty-the-cart"),
            run_git(self.repository, "rev-parse", "main"),
        )
