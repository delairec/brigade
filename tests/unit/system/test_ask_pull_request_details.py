import unittest

from brigade.errors import BrigadeError
from brigade.system.ask_pull_request_details import PullRequestDetailsQuery, ask_pull_request_details

NO_RUNTIME_NEEDED = None
QUERY = PullRequestDetailsQuery(repository="/projects/shop", number=12, environment={"GH_TOKEN": "token-of-octo-cli"})


class ForgeDouble:
    def __init__(self, answer):
        self.answer = answer

    def read_pull_request(self, request, runtime):
        return self.answer


class AskPullRequestDetailsTest(unittest.TestCase):
    def test_should_refuse_an_answer_lacking_the_pull_request_naming_the_forge(self):
        # Arrange
        forge = ForgeDouble({"schema_version": 1})

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            ask_pull_request_details(forge, "github", QUERY, NO_RUNTIME_NEEDED)

        # Assert
        self.assertEqual(
            str(refusal.exception), "forge plugin github answered read_pull_request: lacks the key pull_request"
        )
