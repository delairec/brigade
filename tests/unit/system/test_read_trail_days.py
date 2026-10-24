import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.system.read_trail_days import read_trail_days

CONFIGURATION = Path("/home/ada/.config/brigade/config.toml")


class ReadTrailDaysTest(unittest.TestCase):
    def test_should_answer_7_when_the_key_is_absent(self):
        # Arrange
        document_without_trail_days = {"client": "fake"}

        # Act
        trail_days = read_trail_days(document_without_trail_days, CONFIGURATION)

        # Assert
        self.assertEqual(trail_days, 7)

    def test_should_answer_the_days_the_key_sets(self):
        # Act
        trail_days = read_trail_days({"trail_days": 30}, CONFIGURATION)

        # Assert
        self.assertEqual(trail_days, 30)

    def test_should_refuse_a_value_that_is_no_integer_of_1_or_more_naming_the_key_and_the_file(self):
        # Arrange
        rows = [
            ("zero", 0, "trail_days is 0, not 1 or more, in /home/ada/.config/brigade/config.toml"),
            ("a negative count", -3, "trail_days is -3, not 1 or more, in /home/ada/.config/brigade/config.toml"),
            ("a number", 1.5, "trail_days is a number, not an integer, in /home/ada/.config/brigade/config.toml"),
            ("a boolean", True, "trail_days is a boolean, not an integer, in /home/ada/.config/brigade/config.toml"),
            ("a string", "7", "trail_days is a string, not an integer, in /home/ada/.config/brigade/config.toml"),
        ]
        for case, value, expected_problem in rows:
            with self.subTest(case=case):
                # Act
                with self.assertRaises(BrigadeError) as raised:
                    read_trail_days({"trail_days": value}, CONFIGURATION)

                # Assert
                self.assertEqual(str(raised.exception), expected_problem)
