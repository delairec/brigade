import unittest

from brigade.ledger.pattern_ratified import PatternRatified


class PatternRatifiedTest(unittest.TestCase):
    def test_should_read_the_pattern_ratified_for_a_project(self):
        # Act
        event = PatternRatified.from_document({"event": "pattern.ratified", "project": "tidepool"})

        # Assert
        self.assertEqual(event, PatternRatified(project="tidepool"))
