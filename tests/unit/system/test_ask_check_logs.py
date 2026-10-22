import unittest

from brigade.errors import BrigadeError
from brigade.system.ask_check_logs import CheckLogsQuery, ask_check_logs

NO_RUNTIME_NEEDED = None
QUERY = CheckLogsQuery(
    repository="/projects/shop", number=12, checks=("tests",), lines=200, environment={"GH_TOKEN": "token-of-octo-cli"}
)


class ForgeDouble:
    def __init__(self, answer):
        self.answer = answer
        self.requests = []

    def read_check_logs(self, request, runtime):
        self.requests.append(request)
        return self.answer


class AskCheckLogsTest(unittest.TestCase):
    def test_should_refuse_an_answer_lacking_the_logs_naming_the_forge(self):
        # Arrange
        forge = ForgeDouble({"schema_version": 1})

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            ask_check_logs(forge, "github", QUERY, NO_RUNTIME_NEEDED)

        # Assert
        self.assertEqual(str(refusal.exception), "forge plugin github answered read_check_logs: lacks the key logs")

    def test_should_answer_the_logs_the_forge_reads(self):
        # Arrange
        forge = ForgeDouble({"schema_version": 1, "logs": [{"name": "tests", "tail": "FAIL test_cart"}]})

        # Act
        logs = ask_check_logs(forge, "github", QUERY, NO_RUNTIME_NEEDED)

        # Assert
        self.assertEqual(logs, [{"name": "tests", "tail": "FAIL test_cart"}])

    def test_should_ask_the_forge_for_the_checks_and_the_lines_of_the_query(self):
        # Arrange
        forge = ForgeDouble({"schema_version": 1, "logs": []})

        # Act
        ask_check_logs(forge, "github", QUERY, NO_RUNTIME_NEEDED)

        # Assert
        self.assertEqual(
            forge.requests,
            [
                {
                    "schema_version": 1,
                    "repository": "/projects/shop",
                    "number": 12,
                    "checks": ["tests"],
                    "lines": 200,
                    "environment": {"GH_TOKEN": "token-of-octo-cli"},
                }
            ],
        )
