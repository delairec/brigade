import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.system.read_runs_kept import read_runs_kept

CONFIGURATION = Path("/home/ada/.config/brigade/config.toml")


class ReadRunsKeptTest(unittest.TestCase):
    def test_should_answer_100_when_the_key_is_absent(self):
        # Arrange
        document_without_runs_kept = {"client": "fake"}

        # Act
        runs_kept = read_runs_kept(document_without_runs_kept, CONFIGURATION)

        # Assert
        self.assertEqual(runs_kept, 100)

    def test_should_answer_the_count_the_key_sets(self):
        # Act
        runs_kept = read_runs_kept({"runs_kept": 20}, CONFIGURATION)

        # Assert
        self.assertEqual(runs_kept, 20)

    def test_should_refuse_a_value_that_is_no_integer_of_1_or_more_naming_the_key_and_the_file(self):
        # Arrange
        rows = [
            ("zero", 0, "runs_kept is 0, not 1 or more, in /home/ada/.config/brigade/config.toml"),
            ("a negative count", -3, "runs_kept is -3, not 1 or more, in /home/ada/.config/brigade/config.toml"),
            ("a number", 1.5, "runs_kept is a number, not an integer, in /home/ada/.config/brigade/config.toml"),
            ("a boolean", True, "runs_kept is a boolean, not an integer, in /home/ada/.config/brigade/config.toml"),
        ]
        for case, value, expected_problem in rows:
            with self.subTest(case=case):
                # Act
                with self.assertRaises(BrigadeError) as raised:
                    read_runs_kept({"runs_kept": value}, CONFIGURATION)

                # Assert
                self.assertEqual(str(raised.exception), expected_problem)
