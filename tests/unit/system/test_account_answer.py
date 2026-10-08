import unittest

from brigade.system.account_answer import AccountAnswer


class AccountAnswerTest(unittest.TestCase):
    def test_should_read_the_login_of_the_active_account(self):
        # Act
        answer = AccountAnswer.from_document({"schema_version": 1, "login": "Clauche-bot"})

        # Assert
        self.assertEqual(answer, AccountAnswer(login="Clauche-bot"))

    def test_should_read_no_login_when_no_account_is_active(self):
        # Act
        answer = AccountAnswer.from_document({"schema_version": 1, "login": None})

        # Assert
        self.assertEqual(answer, AccountAnswer(login=None))
