import unittest

from brigade.errors import BrigadeError
from brigade.tasks.read_task_number import read_task_number


class ReadTaskNumberTest(unittest.TestCase):
    def test_should_read_the_number_that_ends_the_name_of_the_task(self):
        for task, expected in [("S3", 3), ("TP146", 146), ("B2B40", 40)]:
            with self.subTest(task=task):
                # Act
                number = read_task_number(task, "M1")

                # Assert
                self.assertEqual(number, expected)

    def test_should_refuse_a_task_whose_name_ends_on_no_number(self):
        # Act
        with self.assertRaises(BrigadeError) as refusal:
            read_task_number("Login", "M1")

        # Assert
        self.assertEqual(str(refusal.exception), "@TASK.Login of the wave M1 carries no number to be ordered by")
