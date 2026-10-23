import unittest

from brigade.errors import BrigadeError
from brigade.system.ask_pull_request_details import PullRequestDetailsQuery, ask_pull_request_details
from tests.unit.forge_double import ForgeDouble

NO_RUNTIME_NEEDED = None
QUERY = PullRequestDetailsQuery(repository="/projects/shop", number=12, environment={"GH_TOKEN": "token-of-octo-cli"})


class AskPullRequestDetailsTest(unittest.TestCase):
    def test_should_refuse_an_answer_lacking_the_pull_request_naming_the_forge(self):
        # Arrange
        forge = ForgeDouble({"read_pull_request": lambda request: {"schema_version": 1}})

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            ask_pull_request_details(forge, "github", QUERY, NO_RUNTIME_NEEDED)

        # Assert
        self.assertEqual(
            str(refusal.exception), "forge plugin github answered read_pull_request: lacks the key pull_request"
        )

    def test_should_answer_the_pull_request_the_forge_describes(self):
        # Arrange
        pull_request = {
            "number": 12,
            "title": "feat: empty the cart",
            "body": "Empty the cart\n",
            "head": "task/w1/S3",
            "head_sha": "4f2a9c1",
            "checks": [],
        }
        forge = ForgeDouble({"read_pull_request": lambda request: {"schema_version": 1, "pull_request": pull_request}})

        # Act
        answered = ask_pull_request_details(forge, "github", QUERY, NO_RUNTIME_NEEDED)

        # Assert
        self.assertEqual(
            answered,
            {
                "number": 12,
                "title": "feat: empty the cart",
                "body": "Empty the cart\n",
                "head": "task/w1/S3",
                "head_sha": "4f2a9c1",
                "checks": [],
            },
        )
