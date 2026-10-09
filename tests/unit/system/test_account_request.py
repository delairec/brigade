import unittest

from brigade.system.account_request import AccountRequest


class AccountRequestTest(unittest.TestCase):
    def test_should_write_the_document_of_an_account_description_with_the_environment_of_its_login(self):
        # Act
        document = AccountRequest(environment={"GH_TOKEN": "token-of-octo-bot"}).to_document()

        # Assert
        self.assertEqual(document, {"schema_version": 1, "environment": {"GH_TOKEN": "token-of-octo-bot"}})
