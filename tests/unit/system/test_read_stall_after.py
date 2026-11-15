import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.system.read_stall_after import read_stall_after

CONFIGURATION = Path("/srv/brigade/config.toml")


class ReadStallAfterTest(unittest.TestCase):
    def test_should_answer_60_minutes_when_the_key_is_absent(self):
        # Arrange
        document_without_stall_after = {"client": "fake"}

        # Act
        stall_after = read_stall_after(document_without_stall_after, CONFIGURATION)

        # Assert
        self.assertEqual(stall_after, 60)

    def test_should_answer_the_minutes_the_key_sets(self):
        # Act
        stall_after = read_stall_after({"stall_after": 90}, CONFIGURATION)

        # Assert
        self.assertEqual(stall_after, 90)

    def test_should_refuse_a_value_that_is_no_integer_of_1_or_more_naming_the_key_and_the_file(self):
        # Arrange
        rows = [
            ("zero", 0, "stall_after is 0, not 1 or more, in /srv/brigade/config.toml"),
            ("a negative count", -5, "stall_after is -5, not 1 or more, in /srv/brigade/config.toml"),
            ("a number", 7.5, "stall_after is a number, not an integer, in /srv/brigade/config.toml"),
            ("a boolean", True, "stall_after is a boolean, not an integer, in /srv/brigade/config.toml"),
        ]
        for case, value, expected_problem in rows:
            with self.subTest(case=case):
                # Act
                with self.assertRaises(BrigadeError) as raised:
                    read_stall_after({"stall_after": value}, CONFIGURATION)

                # Assert
                self.assertEqual(str(raised.exception), expected_problem)
