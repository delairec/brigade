import unittest

from brigade.system.read_start_time import read_start_time


class ReadStartTimeTest(unittest.TestCase):
    def test_should_read_the_start_time_whatever_the_name_of_the_process(self):
        rows = [
            (
                "a plain name",
                "4242 (sleep) S 1 4242 4242 0 -1 4194560 100 0 0 0 0 0 0 0 20 0 1 0 987654 8192000 200\n",
            ),
            (
                "a name holding spaces and a closing parenthesis",
                "4242 (sleep) 9 9) S 1 4242 4242 0 -1 4194560 100 0 0 0 0 0 0 0 20 0 1 0 987654 8192000 200\n",
            ),
        ]
        for case, stat in rows:
            with self.subTest(case=case):
                # Act
                start_time = read_start_time(stat)

                # Assert
                self.assertEqual(start_time, 987654)
