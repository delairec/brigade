import unittest
from datetime import timedelta

from brigade.system.read_since import read_since


class ReadSinceADayCountTest(unittest.TestCase):
    def test_should_read_that_many_days_back(self):
        # Act
        since = read_since("7d")

        # Assert
        self.assertEqual(since, timedelta(days=7))
