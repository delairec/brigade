import unittest

from brigade.errors import BrigadeError
from brigade.system.ask_pull_request import PullRequestQuery, ask_pull_request
from brigade.system.pull_request_facts import CheckVerdict, PullRequestFacts

NO_RUNTIME_NEEDED = None
QUERY = PullRequestQuery(
    repository="/projects/shop", branch="task/M1-empty-cart/S3", environment={"GH_TOKEN": "token-of-octo-cli"}
)


class ForgeDouble:
    def __init__(self, answer):
        self.answer = answer
        self.requests = []

    def find_pull_request(self, request, runtime):
        self.requests.append(request)
        return self.answer


class AskPullRequestTest(unittest.TestCase):
    def test_should_send_the_repository_the_branch_and_the_environment_and_read_the_pull_request(self):
        # Arrange
        forge = ForgeDouble(
            {
                "schema_version": 1,
                "pull_request": {
                    "number": 42,
                    "state": "open",
                    "checks": [{"name": "tests", "verdict": "success"}],
                    "review": "approved",
                    "behind": False,
                    "head": "0123abc",
                },
            }
        )

        # Act
        pull_request = ask_pull_request(forge, "github", QUERY, NO_RUNTIME_NEEDED)

        # Assert
        self.assertEqual(
            (forge.requests, pull_request),
            (
                [
                    {
                        "schema_version": 1,
                        "repository": "/projects/shop",
                        "branch": "task/M1-empty-cart/S3",
                        "environment": {"GH_TOKEN": "token-of-octo-cli"},
                    }
                ],
                PullRequestFacts(
                    number=42,
                    state="open",
                    checks=(CheckVerdict(name="tests", verdict="success"),),
                    review="approved",
                    behind=False,
                    head="0123abc",
                ),
            ),
        )

    def test_should_answer_none_when_the_branch_has_no_pull_request(self):
        # Arrange
        forge = ForgeDouble({"schema_version": 1, "pull_request": None})

        # Act
        pull_request = ask_pull_request(forge, "github", QUERY, NO_RUNTIME_NEEDED)

        # Assert
        self.assertIsNone(pull_request)

    def test_should_refuse_an_answer_lacking_the_pull_request_naming_the_forge(self):
        # Arrange
        forge = ForgeDouble({"schema_version": 1})

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            ask_pull_request(forge, "github", QUERY, NO_RUNTIME_NEEDED)

        # Assert
        self.assertEqual(
            str(refusal.exception), "forge plugin github answered find_pull_request: lacks the key pull_request"
        )
