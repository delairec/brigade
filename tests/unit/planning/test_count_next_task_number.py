import unittest

from brigade.planning.count_next_task_number import count_next_task_number


class CountNextTaskNumberTest(unittest.TestCase):
    def test_should_answer_the_first_number_of_a_corpus_without_tasks(self):
        # Arrange
        no_entities = []

        # Act
        number = count_next_task_number(no_entities)

        # Assert
        self.assertEqual(number, 1)

    def test_should_answer_the_number_after_the_highest_task_number_whatever_the_prefix(self):
        # Arrange
        entities = [{"type": "TASK", "name": "B7"}, {"type": "TASK", "name": "FIX12"}, {"type": "TASK", "name": "B2"}]

        # Act
        number = count_next_task_number(entities)

        # Assert
        self.assertEqual(number, 13)

    def test_should_leave_out_the_numbers_of_the_other_types(self):
        # Arrange
        entities = [{"type": "DECISION", "name": "D40"}, {"type": "TASK", "name": "B2"}]

        # Act
        number = count_next_task_number(entities)

        # Assert
        self.assertEqual(number, 3)
