import unittest

from brigade.errors import BrigadeError
from brigade.system.account_answer import AccountAnswer
from brigade.system.ask_forge_account import ask_forge_account

NO_RUNTIME_NEEDED = None
UNBOUND_ENVIRONMENT = {}


class ForgeDouble:
    def __init__(self, answer):
        self.answer = answer
        self.requests = []

    def describe_account(self, request, runtime):
        self.requests.append(request)
        return self.answer


class AskForgeAccountTest(unittest.TestCase):
    def test_should_send_the_versioned_request_and_read_the_login(self):
        # Arrange
        forge = ForgeDouble({"schema_version": 1, "login": "Clauche-bot"})

        # Act
        account = ask_forge_account(forge, "github", UNBOUND_ENVIRONMENT, NO_RUNTIME_NEEDED)

        # Assert
        self.assertEqual(forge.requests, [{"schema_version": 1, "environment": {}}])
        self.assertEqual(account, AccountAnswer(login="Clauche-bot"))

    def test_should_refuse_an_answer_lacking_the_login_naming_the_forge(self):
        # Arrange
        forge = ForgeDouble({"schema_version": 1})

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            ask_forge_account(forge, "github", UNBOUND_ENVIRONMENT, NO_RUNTIME_NEEDED)

        # Assert
        self.assertEqual(str(refusal.exception), "forge plugin github answered describe_account: lacks the key login")
