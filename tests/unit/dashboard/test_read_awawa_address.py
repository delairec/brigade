import unittest

from brigade.dashboard.awawa_address import AwawaAddress
from brigade.dashboard.read_awawa_address import read_awawa_address


class ReadAwawaAddressTest(unittest.TestCase):
    def test_should_read_the_project_and_the_parameters_of_the_tab_without_the_project_chosen_or_a_blank(self):
        # Act
        address = read_awawa_address("awawa/oak?view=board&type=TASK&filter=STATUS%3Dtodo&project=oak&search=")

        # Assert
        self.assertEqual(
            address,
            AwawaAddress(project="oak", parameters=(("view", "board"), ("type", "TASK"), ("filter", "STATUS=todo"))),
        )

    def test_should_read_a_project_whose_name_is_quoted(self):
        # Act
        address = read_awawa_address("awawa/my%20oak")

        # Assert
        self.assertEqual(address, AwawaAddress(project="my oak"))

    def test_should_read_no_address_out_of_the_tab_of_one_project(self):
        rows = [
            ("the tab without a project", "awawa"),
            ("an empty project", "awawa/"),
            ("a path below the project", "awawa/oak/extra"),
            ("another view", "status"),
            ("a view starting with the same word", "awawaoak"),
        ]
        for case, target in rows:
            with self.subTest(case):
                # Act
                address = read_awawa_address(target)

                # Assert
                self.assertIsNone(address)
