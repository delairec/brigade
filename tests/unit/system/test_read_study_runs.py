import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.system.read_study_runs import read_study_runs

CONFIGURATION = Path("/home/ada/.config/brigade/config.toml")


class ReadStudyRunsTest(unittest.TestCase):
    def test_should_answer_2_when_the_key_is_absent(self):
        # Arrange
        document_without_study_runs = {"client": "fake"}

        # Act
        study_runs = read_study_runs(document_without_study_runs, CONFIGURATION)

        # Assert
        self.assertEqual(study_runs, 2)

    def test_should_answer_the_count_the_key_sets(self):
        # Act
        study_runs = read_study_runs({"study_runs": 5}, CONFIGURATION)

        # Assert
        self.assertEqual(study_runs, 5)

    def test_should_refuse_a_value_that_is_no_integer_of_1_or_more_naming_the_key_and_the_file(self):
        for case, value, expected_problem in [
            ("zero", 0, "study_runs is 0, not 1 or more, in /home/ada/.config/brigade/config.toml"),
            ("a negative count", -1, "study_runs is -1, not 1 or more, in /home/ada/.config/brigade/config.toml"),
            ("a string", "two", "study_runs is a string, not an integer, in /home/ada/.config/brigade/config.toml"),
            ("a boolean", True, "study_runs is a boolean, not an integer, in /home/ada/.config/brigade/config.toml"),
        ]:
            with self.subTest(case=case):
                # Act
                with self.assertRaises(BrigadeError) as raised:
                    read_study_runs({"study_runs": value}, CONFIGURATION)

                # Assert
                self.assertEqual(str(raised.exception), expected_problem)
