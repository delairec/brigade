from tests.cli.temporary_machine import CLONE_ENTRY_POINT
from tests.cli.test_task import MILESTONE_BRANCH
from tests.cli.test_verify_preflight import VerifyPreflightTestCase


class BrigadePreflightVerifyPullRequestTest(VerifyPreflightTestCase):
    def test_should_print_one_line_per_check_of_the_preflight(self):
        # Arrange
        self.describe_pull_request()

        # Act
        completed = self.machine.run_brigade(
            CLONE_ENTRY_POINT,
            "preflight",
            "verify-pull-request",
            "pr=42",
            "task=S3",
            f"base={MILESTONE_BRANCH}",
            environment=self.describe_environment(),
            cwd=self.worktree,
        )

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stdout,
            "preflight verify-pull-request\npass  ancestry\npass  checks\npass  corpus\npass  promotion\n"
            "pass  untouched_files\npass  privacy\npass  body\n",
        )
