import unittest

from brigade.ledger.omit_absent_pull_request import omit_absent_pull_request


class OmitAbsentPullRequestTest(unittest.TestCase):
    def test_should_keep_the_number_of_a_pull_request(self):
        # Act
        fields = omit_absent_pull_request(41)

        # Assert
        self.assertEqual(fields, {"pr": 41})

    def test_should_leave_out_a_pull_request_that_is_absent(self):
        # Arrange
        no_pull_request = None

        # Act
        fields = omit_absent_pull_request(no_pull_request)

        # Assert
        self.assertEqual(fields, {})
