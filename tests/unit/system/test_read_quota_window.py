import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.system.read_quota_window import read_quota_window

CONFIGURATION_PATH = Path("/srv/brigade/config.toml")


class ReadQuotaWindowTest(unittest.TestCase):
    def test_should_answer_the_hours_the_key_sets(self):
        # Act
        hours = read_quota_window({"quota_window_hours": 8}, CONFIGURATION_PATH)

        # Assert
        self.assertEqual(hours, 8)

    def test_should_answer_five_hours_when_the_key_is_absent(self):
        # Arrange
        no_key = {}

        # Act
        hours = read_quota_window(no_key, CONFIGURATION_PATH)

        # Assert
        self.assertEqual(hours, 5)

    def test_should_refuse_a_value_that_is_not_a_positive_integer(self):
        # Arrange
        rows = [
            ("a string", "5", "quota_window_hours is a string, not an integer, in"),
            ("a boolean", True, "quota_window_hours is a boolean, not an integer, in"),
            ("a float", 2.5, "quota_window_hours is a number, not an integer, in"),
            ("zero", 0, "quota_window_hours is 0, not 1 or more, in"),
        ]
        for case, value, message in rows:
            with self.subTest(case=case):
                # Act
                with self.assertRaises(BrigadeError) as raised:
                    read_quota_window({"quota_window_hours": value}, CONFIGURATION_PATH)

                # Assert
                self.assertEqual(str(raised.exception), f"{message} {CONFIGURATION_PATH}")
