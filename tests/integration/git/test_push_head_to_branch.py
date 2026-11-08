from pathlib import Path

from brigade.git.push_branch import BranchPush
from brigade.git.push_head_to_branch import push_head_to_branch
from tests.integration.repository_test_case import IDENTITY, RepositoryTestCase
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


class PushHeadToBranchTest(RepositoryTestCase):
    def setUp(self):
        super().setUp()
        root = Path(self.root.name)
        self.remote = root / "remote.git"
        self.detached = root / "detached"
        run_git(self.repository, "init", "--quiet", "--bare", str(self.remote))
        run_git(self.repository, "remote", "add", "origin", str(self.remote))
        run_git(self.repository, "branch", "integration/hardening")
        run_git(self.repository, "push", "--quiet", "origin", "integration/hardening")
        run_git(self.repository, "worktree", "add", "--quiet", "--detach", str(self.detached), "main")
        run_git(self.detached, *IDENTITY, "commit", "--quiet", "--allow-empty", "-m", "report")

    def push_detached_head(self) -> None:
        push_head_to_branch(
            run_process_without_trail,
            BranchPush(repository=self.detached, branch="integration/hardening", environment=NO_ENVIRONMENT),
        )

    def test_should_move_the_branch_of_the_remote_to_the_head_of_a_detached_checkout(self):
        # Act
        self.push_detached_head()

        # Assert
        self.assertEqual(
            run_git(self.remote, "rev-parse", "integration/hardening"),
            run_git(self.detached, "rev-parse", "HEAD"),
        )

    def test_should_leave_the_local_branch_of_that_name_where_it_stands(self):
        # Arrange
        local_head = run_git(self.repository, "rev-parse", "integration/hardening")

        # Act
        self.push_detached_head()

        # Assert
        self.assertEqual(run_git(self.repository, "rev-parse", "integration/hardening"), local_head)
