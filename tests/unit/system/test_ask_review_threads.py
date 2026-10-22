import unittest

from brigade.errors import BrigadeError
from brigade.system.ask_review_threads import ReviewThreadsQuery, ask_review_threads

NO_RUNTIME_NEEDED = None
QUERY = ReviewThreadsQuery(repository="/projects/shop", number=12, environment={"GH_TOKEN": "token-of-octo-cli"})


class ForgeDouble:
    def __init__(self, answer):
        self.answer = answer
        self.requests = []

    def list_review_threads(self, request, runtime):
        self.requests.append(request)
        return self.answer


class AskReviewThreadsTest(unittest.TestCase):
    def test_should_refuse_an_answer_lacking_the_threads_naming_the_forge(self):
        # Arrange
        forge = ForgeDouble({"schema_version": 1})

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            ask_review_threads(forge, "github", QUERY, NO_RUNTIME_NEEDED)

        # Assert
        self.assertEqual(
            str(refusal.exception), "forge plugin github answered list_review_threads: lacks the key threads"
        )

    def test_should_answer_the_threads_the_forge_lists(self):
        # Arrange
        thread = {"id": "PRRT_kwDOA1", "file": "src/cart.py", "line": 12, "author": "octo", "body": "wrong total"}
        forge = ForgeDouble({"schema_version": 1, "threads": [thread]})

        # Act
        threads = ask_review_threads(forge, "github", QUERY, NO_RUNTIME_NEEDED)

        # Assert
        self.assertEqual(
            threads,
            [{"id": "PRRT_kwDOA1", "file": "src/cart.py", "line": 12, "author": "octo", "body": "wrong total"}],
        )

    def test_should_ask_the_forge_for_the_threads_of_the_pull_request_of_the_query(self):
        # Arrange
        forge = ForgeDouble({"schema_version": 1, "threads": []})

        # Act
        ask_review_threads(forge, "github", QUERY, NO_RUNTIME_NEEDED)

        # Assert
        self.assertEqual(
            forge.requests,
            [
                {
                    "schema_version": 1,
                    "repository": "/projects/shop",
                    "number": 12,
                    "environment": {"GH_TOKEN": "token-of-octo-cli"},
                }
            ],
        )
