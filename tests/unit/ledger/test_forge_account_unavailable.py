import unittest

from brigade.ledger.forge_account_unavailable import ForgeAccountUnavailable


class ForgeAccountUnavailableTest(unittest.TestCase):
    def test_should_read_the_login_and_the_key_bound_to_it(self):
        # Act
        event = ForgeAccountUnavailable.from_document(
            {"event": "forge_account.unavailable", "login": "octo-bot", "key": "cli"}
        )

        # Assert
        self.assertEqual(event, ForgeAccountUnavailable(login="octo-bot", key="cli"))

    def test_should_write_the_login_and_the_key_bound_to_it(self):
        # Act
        document = ForgeAccountUnavailable(login="octo-bot", key="verify").to_document()

        # Assert
        self.assertEqual(document, {"login": "octo-bot", "key": "verify"})
