import unittest

from brigade.system.account_request import AccountRequest


class AccountRequestTest(unittest.TestCase):
    def test_should_write_the_document_of_an_account_description(self):
        # Act
        document = AccountRequest().to_document()

        # Assert
        self.assertEqual(document, {"schema_version": 1})
