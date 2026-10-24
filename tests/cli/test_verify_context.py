import json

from tests.cli.temporary_machine import CLONE_ENTRY_POINT
from tests.cli.test_verify_preflight import VerifyPreflightTestCase


class VerifyContextTestCase(VerifyPreflightTestCase):
    def run_verify_context(self, *arguments: str):
        return self.machine.run_brigade(
            CLONE_ENTRY_POINT,
            "verify",
            "context",
            *arguments,
            environment=self.describe_environment(),
            cwd=self.project.path,
        )


class BrigadeVerifyContextOfAPullRequestTest(VerifyContextTestCase):
    def test_should_name_the_pull_request_its_task_and_its_head(self):
        # Act
        completed = self.run_verify_context("42", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stderr, "")
        document = json.loads(completed.stdout)
        self.assertEqual(document["project"], "shop")
        self.assertEqual(document["pr"], 42)
        self.assertEqual(document["task"], "S3")
        self.assertEqual(document["head"], self.read_head())
