import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.system.read_tick_stale_after import read_tick_stale_after

CONFIGURATION = Path("/home/ada/.config/brigade/config.toml")


class ReadTickStaleAfterTest(unittest.TestCase):
    def test_should_answer_15_minutes_when_the_key_is_absent(self):
        # Arrange
        document_without_tick_stale_after = {"client": "fake"}

        # Act
        tick_stale_after = read_tick_stale_after(document_without_tick_stale_after, CONFIGURATION)

        # Assert
        self.assertEqual(tick_stale_after, 15)

    def test_should_answer_the_minutes_the_key_sets(self):
        # Act
        tick_stale_after = read_tick_stale_after({"tick_stale_after": 30}, CONFIGURATION)

        # Assert
        self.assertEqual(tick_stale_after, 30)

    def test_should_refuse_a_value_that_is_no_integer_of_1_or_more_naming_the_key_and_the_file(self):
        # Arrange
        rows = [
            ("zero", 0, "tick_stale_after is 0, not 1 or more, in /home/ada/.config/brigade/config.toml"),
            ("a negative count", -5, "tick_stale_after is -5, not 1 or more, in /home/ada/.config/brigade/config.toml"),
            (
                "a number",
                7.5,
                "tick_stale_after is a number, not an integer, in /home/ada/.config/brigade/config.toml",
            ),
            (
                "a boolean",
                True,
                "tick_stale_after is a boolean, not an integer, in /home/ada/.config/brigade/config.toml",
            ),
        ]
        for case, value, expected_problem in rows:
            with self.subTest(case=case):
                # Act
                with self.assertRaises(BrigadeError) as raised:
                    read_tick_stale_after({"tick_stale_after": value}, CONFIGURATION)

                # Assert
                self.assertEqual(str(raised.exception), expected_problem)
