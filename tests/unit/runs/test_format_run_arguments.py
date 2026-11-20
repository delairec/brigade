import unittest

from brigade.runs.format_run_arguments import format_run_arguments

NO_ARGUMENTS = {}


class FormatRunArgumentsTest(unittest.TestCase):
    def test_should_print_each_argument_as_key_and_value_sorted_by_key(self):
        # Act
        text = format_run_arguments({"task": "@TASK.B82", "base": "integration/oak"})

        # Assert
        self.assertEqual(text, "base=integration/oak task=@TASK.B82")

    def test_should_print_an_absent_mark_for_a_run_without_argument(self):
        # Act
        text = format_run_arguments(NO_ARGUMENTS)

        # Assert
        self.assertEqual(text, "-")
