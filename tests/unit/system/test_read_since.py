import argparse
import unittest
from datetime import timedelta

from brigade.system.read_since import read_since


class ReadSinceADayCountTest(unittest.TestCase):
    def test_should_read_that_many_days_back(self):
        # Act
        since = read_since("7d")

        # Assert
        self.assertEqual(since, timedelta(days=7))


class ReadSinceNeitherADayCountNorADayTest(unittest.TestCase):
    def test_should_refuse_naming_both_forms(self):
        # Act
        with self.assertRaises(argparse.ArgumentTypeError) as raised:
            read_since("last week")

        # Assert
        self.assertEqual(str(raised.exception), "'last week' is neither <n>d nor a day YYYY-MM-DD")
