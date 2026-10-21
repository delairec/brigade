import unittest

from brigade.tasks.find_task_number import find_task_number


class FindTaskNumberTest(unittest.TestCase):
    def test_should_find_the_number_that_ends_the_name_of_the_task(self):
        for task, expected in [("S3", 3), ("TP146", 146), ("Cleanup", None)]:
            with self.subTest(task=task):
                # Act
                number = find_task_number(task)

                # Assert
                self.assertEqual(number, expected)
