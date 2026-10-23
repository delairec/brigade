import unittest

from brigade.errors import BrigadeError
from brigade.system.ask_pull_requests import PullRequestsQuery, ask_pull_requests
from tests.unit.forge_double import ForgeDouble

NO_RUNTIME_NEEDED = None
QUERY = PullRequestsQuery(repository="/projects/shop", state="open", environment={"GH_TOKEN": "token-of-octo-cli"})


class AskPullRequestsTest(unittest.TestCase):
    def test_should_refuse_an_answer_lacking_the_pull_requests_naming_the_forge(self):
        # Arrange
        forge = ForgeDouble({"list_pull_requests": lambda request: {"schema_version": 1}})

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            ask_pull_requests(forge, "github", QUERY, NO_RUNTIME_NEEDED)

        # Assert
        self.assertEqual(
            str(refusal.exception), "forge plugin github answered list_pull_requests: lacks the key pull_requests"
        )


class AskPullRequestsAnsweredTest(unittest.TestCase):
    def test_should_answer_the_pull_requests_the_forge_lists(self):
        # Arrange
        forge = ForgeDouble(
            {"list_pull_requests": lambda request: {"schema_version": 1, "pull_requests": [{"number": 7}]}}
        )
        query = PullRequestsQuery(repository="/projects/shop", state="open", environment={})

        # Act
        pull_requests = ask_pull_requests(forge, "github", query, None)

        # Assert
        self.assertEqual(pull_requests, [{"number": 7}])
