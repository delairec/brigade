import unittest

from brigade.errors import BrigadeError
from brigade.system.ask_check_runs import CheckRunsQuery, ask_check_runs
from tests.unit.forge_double import ForgeDouble

NO_RUNTIME_NEEDED = None
QUERY = CheckRunsQuery(repository="/projects/shop", branch="main", environment={"GH_TOKEN": "token-of-octo-cli"})
FAILED_TESTS = {
    "pull_request": 12,
    "branch": "task/shop_w1/S3",
    "head": "0123abc",
    "name": "tests",
    "conclusion": "failure",
    "link": "https://github.com/octo/shop/actions/runs/7/job/70",
}


class AskCheckRunsTest(unittest.TestCase):
    def test_should_refuse_an_answer_lacking_the_check_runs_naming_the_forge(self):
        # Arrange
        forge = ForgeDouble({"list_check_runs": lambda request: {"schema_version": 1}})

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            ask_check_runs(forge, "github", QUERY, NO_RUNTIME_NEEDED)

        # Assert
        self.assertEqual(
            str(refusal.exception), "forge plugin github answered list_check_runs: lacks the key check_runs"
        )

    def test_should_answer_the_check_runs_the_forge_lists(self):
        # Arrange
        forge = ForgeDouble({"list_check_runs": lambda request: {"schema_version": 1, "check_runs": [FAILED_TESTS]}})

        # Act
        check_runs = ask_check_runs(forge, "github", QUERY, NO_RUNTIME_NEEDED)

        # Assert
        self.assertEqual(
            check_runs,
            [
                {
                    "pull_request": 12,
                    "branch": "task/shop_w1/S3",
                    "head": "0123abc",
                    "name": "tests",
                    "conclusion": "failure",
                    "link": "https://github.com/octo/shop/actions/runs/7/job/70",
                }
            ],
        )

    def test_should_ask_the_forge_for_the_check_runs_of_the_repository_and_its_branch(self):
        # Arrange
        forge = ForgeDouble({"list_check_runs": lambda request: {"schema_version": 1, "check_runs": []}})

        # Act
        ask_check_runs(forge, "github", QUERY, NO_RUNTIME_NEEDED)

        # Assert
        self.assertEqual(
            forge.list_requests("list_check_runs"),
            [
                {
                    "schema_version": 1,
                    "repository": "/projects/shop",
                    "branch": "main",
                    "environment": {"GH_TOKEN": "token-of-octo-cli"},
                }
            ],
        )
