import unittest

from brigade.planning.mark_request_planned import mark_request_planned


class MarkRequestPlannedTest(unittest.TestCase):
    def test_should_mark_the_request_planned_on_its_milestone_and_pull_request(self):
        # Arrange
        text = 'REQUEST oak_r1\n\tTEXT "print"\n\tSTATUS planning\n\nREQUEST oak_r2\n\tSTATUS planning\n'

        # Act
        marked = mark_request_planned(text, "oak_r1", "F1", 42)

        # Assert
        self.assertEqual(
            marked,
            "REQUEST oak_r1\n"
            '\tTEXT "print"\n'
            "\tSTATUS planned\n"
            '\tMILESTONE "F1"\n'
            "\tPR 42\n"
            "\n"
            "REQUEST oak_r2\n"
            "\tSTATUS planning\n",
        )

    def test_should_mark_the_request_planned_with_no_pull_request_when_the_plan_is_merged_at_once(self):
        # Arrange
        text = "REQUEST oak_r1\n\tSTATUS planning\n"
        merged_at_once = None

        # Act
        marked = mark_request_planned(text, "oak_r1", "F1", merged_at_once)

        # Assert
        self.assertEqual(marked, 'REQUEST oak_r1\n\tSTATUS planned\n\tMILESTONE "F1"\n')
