import unittest

from brigade.errors import BrigadeError
from brigade.studies.refuse_inbox_output import refuse_inbox_output


class RefuseInboxOutputTest(unittest.TestCase):
    def test_should_refuse_the_inbox_as_an_output(self):
        # Act
        with self.assertRaises(BrigadeError) as refusal:
            refuse_inbox_output("inbox")

        # Assert
        self.assertEqual(str(refusal.exception), "the output inbox is refused: the inbox has no store until @TASK.B22")

    def test_should_let_any_other_output_through(self):
        # Act
        refused = refuse_inbox_output("issue")

        # Assert
        self.assertIsNone(refused)
