import unittest
from datetime import UTC, datetime

from brigade.system.read_trail_instant import read_trail_instant


class ReadTrailInstantTest(unittest.TestCase):
    def test_should_read_the_instant_that_opens_the_name_of_a_trail(self):
        # Act
        instant = read_trail_instant("20261007T120000Z-4f2a.jsonl")

        # Assert
        self.assertEqual(instant, datetime(2026, 10, 7, 12, 0, 0, tzinfo=UTC))

    def test_should_read_no_instant_from_a_name_that_opens_on_none(self):
        # Act
        instant = read_trail_instant("notes.jsonl")

        # Assert
        self.assertIsNone(instant)
