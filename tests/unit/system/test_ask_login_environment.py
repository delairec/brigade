import unittest

from brigade.errors import BrigadeError
from brigade.system.ask_login_environment import ask_login_environment
from tests.unit.forge_double import ForgeDouble, ForgeRequest

NO_RUNTIME_NEEDED = None


class AskLoginEnvironmentTest(unittest.TestCase):
    def test_should_send_the_login_and_read_its_environment(self):
        # Arrange
        forge = ForgeDouble(
            {
                "read_login_environment": lambda request: {
                    "schema_version": 1,
                    "environment": {"GH_TOKEN": "token-of-octo-bot"},
                }
            }
        )

        # Act
        environment = ask_login_environment(forge, "github", "octo-bot", NO_RUNTIME_NEEDED)

        # Assert
        self.assertEqual(
            forge.requests, [ForgeRequest("read_login_environment", {"schema_version": 1, "login": "octo-bot"})]
        )
        self.assertEqual(environment, {"GH_TOKEN": "token-of-octo-bot"})

    def test_should_answer_none_when_the_forge_holds_no_token_for_the_login(self):
        # Arrange
        forge = ForgeDouble({"read_login_environment": lambda request: {"schema_version": 1, "environment": None}})

        # Act
        environment = ask_login_environment(forge, "github", "octo-bot", NO_RUNTIME_NEEDED)

        # Assert
        self.assertIsNone(environment)

    def test_should_refuse_an_answer_lacking_the_environment_naming_the_forge(self):
        # Arrange
        forge = ForgeDouble({"read_login_environment": lambda request: {"schema_version": 1}})

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            ask_login_environment(forge, "github", "octo-bot", NO_RUNTIME_NEEDED)

        # Assert
        self.assertEqual(
            str(refusal.exception), "forge plugin github answered read_login_environment: lacks the key environment"
        )
