import unittest

from brigade.runs.decide_run_exit_code import decide_run_exit_code


class DecideRunExitCodeTest(unittest.TestCase):
    def test_should_give_each_outcome_its_code_ranged_by_severity(self):
        rows = [
            ("done", 0),
            ("failed", 1),
            ("undeclared", 3),
            ("blocked", 10),
            ("wall_limit", 11),
            ("turn_limit", 12),
            ("handed_over", 20),
        ]
        for outcome, expected_code in rows:
            with self.subTest(outcome=outcome):
                # Act
                code = decide_run_exit_code(outcome)

                # Assert
                self.assertEqual(code, expected_code)

    def test_should_give_the_code_of_failed_to_a_run_dead_without_an_outcome(self):
        # Arrange
        no_outcome = None

        # Act
        code = decide_run_exit_code(no_outcome)

        # Assert
        self.assertEqual(code, 1)
