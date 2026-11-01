import argparse
import unittest

from brigade.ledger.read_reference import read_reference


class ReadReferenceTest(unittest.TestCase):
    def test_should_read_the_measure_and_its_figure(self):
        for text, expected in [
            ("steps_to_first_edit_p50=23", ("steps_to_first_edit_p50", 23.0)),
            ("task_run_steps_p50=47", ("task_run_steps_p50", 47.0)),
            ("oversized_output_steps_per_launch=2.18", ("oversized_output_steps_per_launch", 2.18)),
        ]:
            with self.subTest(text=text):
                # Act
                reference = read_reference(text)

                # Assert
                self.assertEqual(reference, expected)

    def test_should_refuse_a_measure_it_does_not_compare(self):
        # Act
        with self.assertRaises(argparse.ArgumentTypeError) as raised:
            read_reference("steps=23")

        # Assert
        self.assertEqual(
            str(raised.exception),
            "'steps' is not a reference measure: steps_to_first_edit_p50, task_run_steps_p50,"
            " oversized_output_steps_per_launch",
        )

    def test_should_refuse_a_figure_that_is_not_a_number(self):
        for text, expected in [
            ("task_run_steps_p50=many", "'many' is not a number"),
            ("task_run_steps_p50", "'' is not a number"),
        ]:
            with self.subTest(text=text):
                # Act
                with self.assertRaises(argparse.ArgumentTypeError) as raised:
                    read_reference(text)

                # Assert
                self.assertEqual(str(raised.exception), expected)
