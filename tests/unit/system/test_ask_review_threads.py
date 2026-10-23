import unittest

from brigade.errors import BrigadeError
from brigade.system.ask_review_threads import ReviewThreadsQuery, ask_review_threads
from tests.unit.forge_double import ForgeDouble, ForgeRequest

NO_RUNTIME_NEEDED = None
QUERY = ReviewThreadsQuery(repository="/projects/shop", number=12, environment={"GH_TOKEN": "token-of-octo-cli"})


class AskReviewThreadsTest(unittest.TestCase):
    def test_should_refuse_an_answer_lacking_the_threads_naming_the_forge(self):
        # Arrange
        forge = ForgeDouble({"list_review_threads": lambda request: {"schema_version": 1}})

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            ask_review_threads(forge, "github", QUERY, NO_RUNTIME_NEEDED)

        # Assert
        self.assertEqual(
            str(refusal.exception), "forge plugin github answered list_review_threads: lacks the key threads"
        )

    def test_should_refuse_an_answer_whose_thread_is_not_an_object_naming_the_forge(self):
        # Arrange
        forge = ForgeDouble({"list_review_threads": lambda request: {"schema_version": 1, "threads": ["wrong total"]}})

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            ask_review_threads(forge, "github", QUERY, NO_RUNTIME_NEEDED)

        # Assert
        self.assertEqual(
            str(refusal.exception),
            "forge plugin github answered list_review_threads: threads[0] is a string, not an object",
        )

    def test_should_answer_the_threads_the_forge_lists(self):
        # Arrange
        thread = {"id": "PRRT_kwDOA1", "file": "src/cart.py", "line": 12, "author": "octo", "body": "wrong total"}
        forge = ForgeDouble({"list_review_threads": lambda request: {"schema_version": 1, "threads": [thread]}})

        # Act
        threads = ask_review_threads(forge, "github", QUERY, NO_RUNTIME_NEEDED)

        # Assert
        self.assertEqual(
            threads,
            [{"id": "PRRT_kwDOA1", "file": "src/cart.py", "line": 12, "author": "octo", "body": "wrong total"}],
        )

    def test_should_ask_the_forge_for_the_threads_of_the_pull_request_of_the_query(self):
        # Arrange
        forge = ForgeDouble({"list_review_threads": lambda request: {"schema_version": 1, "threads": []}})

        # Act
        ask_review_threads(forge, "github", QUERY, NO_RUNTIME_NEEDED)

        # Assert
        self.assertEqual(
            forge.requests,
            [
                ForgeRequest(
                    "list_review_threads",
                    {
                        "schema_version": 1,
                        "repository": "/projects/shop",
                        "number": 12,
                        "environment": {"GH_TOKEN": "token-of-octo-cli"},
                    },
                )
            ],
        )
