import unittest

from brigade.commands.run import COMMAND


class RunTextTest(unittest.TestCase):
    def test_should_count_the_segments_of_a_run_handed_over(self):
        # Arrange
        document = {
            "run": "20261007T090000Z-b70a01",
            "procedure": "deliver",
            "role": "builder",
            "slot": "build",
            "outcome": "done",
            "segments": 2,
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, "run 20261007T090000Z-b70a01: deliver as builder (build) done after 2 segments")


class RunExtraArgumentTest(unittest.TestCase):
    def test_should_accept_after_the_options_a_key_value_argument_alone(self):
        rows = [
            ("an argument of the procedure", "task=B06", True),
            ("an unknown option", "--frobnicate", False),
            ("a word with no key", "B06", False),
        ]
        for case, extra, expected_acceptance in rows:
            with self.subTest(case=case):
                # Act
                accepted = COMMAND.accept_extra_argument(extra)

                # Assert
                self.assertIs(accepted, expected_acceptance)
