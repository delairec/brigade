import unittest

from brigade.processes.is_failed_record import is_failed_record


class IsFailedRecordTest(unittest.TestCase):
    def test_should_count_as_failed_anything_but_an_exit_at_zero(self):
        for record, expected in [
            ({"outcome": "exited", "exit": 0}, False),
            ({"outcome": "exited", "exit": 1}, True),
            ({"outcome": "timed_out", "exit": None}, True),
        ]:
            with self.subTest(record=record):
                # Act
                failed = is_failed_record(record)

                # Assert
                self.assertEqual(failed, expected)
