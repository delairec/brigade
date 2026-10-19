import unittest

from brigade.planning.mark_request_planned import mark_request_planned


class MarkRequestPlannedTest(unittest.TestCase):
    def test_should_mark_the_request_planned_on_its_milestone_and_branch(self):
        # Arrange
        text = 'REQUEST oak_1\n\tTEXT "print"\n\tSTATUS planning\n\nREQUEST oak_2\n\tSTATUS planning\n'

        # Act
        marked = mark_request_planned(text, "oak_1", "F1", "integration/F1-printer")

        # Assert
        self.assertEqual(
            marked,
            "REQUEST oak_1\n"
            '\tTEXT "print"\n'
            "\tSTATUS planned\n"
            '\tMILESTONE "F1"\n'
            '\tBRANCH "integration/F1-printer"\n'
            "\n"
            "REQUEST oak_2\n"
            "\tSTATUS planning\n",
        )
