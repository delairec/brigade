import unittest

from brigade.studies.ask_for_repeats import ask_for_repeats

QUESTION = "Group the families of new signals into patterns."


class AskForRepeatsTest(unittest.TestCase):
    def test_should_ask_a_repeat_to_name_the_pattern_it_repeats_where_the_installed_schema_declares_repeats(self):
        # Arrange
        declared_fields = ("TITLE", "STATUS", "EVIDENCE", "ACTION", "RECIPE", "TARGET", "REPEATS")

        # Act
        question = ask_for_repeats(QUESTION, declared_fields)

        # Assert
        self.assertEqual(
            question,
            "Group the families of new signals into patterns. A new PATTERN that repeats a PATTERN the registry"
            " holds all the same names it in REPEATS, @PATTERN.<its name>.",
        )

    def test_should_ask_the_question_of_today_where_the_installed_schema_declares_no_repeats(self):
        # Arrange
        declared_fields = ("TITLE", "STATUS", "EVIDENCE", "ACTION", "RECIPE", "TARGET")

        # Act
        question = ask_for_repeats(QUESTION, declared_fields)

        # Assert
        self.assertEqual(question, "Group the families of new signals into patterns.")
