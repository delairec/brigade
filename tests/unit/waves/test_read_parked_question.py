import unittest

from brigade.waves.read_parked_question import read_parked_question


class ReadParkedQuestionTest(unittest.TestCase):
    def test_should_read_the_question_of_a_park_on_a_run_that_ended_blocked(self):
        # Arrange
        reason = "run 20261109T013502Z-4c324f blocked: Which forge does the check run against?"

        # Act
        question = read_parked_question(reason)

        # Assert
        self.assertEqual(question, "Which forge does the check run against?")

    def test_should_read_no_question_from_a_park_of_any_other_cause(self):
        for reason in [
            "run dead: 20261109T013502Z-4c324f",
            "past 2 repair rounds",
            "blocked",
            "setup failed",
            "pull request closed",
        ]:
            with self.subTest(reason=reason):
                # Act
                question = read_parked_question(reason)

                # Assert
                self.assertIsNone(question)


if __name__ == "__main__":
    unittest.main()
