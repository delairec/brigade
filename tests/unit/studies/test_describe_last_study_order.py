import unittest
from datetime import UTC, datetime

from brigade.studies.describe_last_study_order import describe_last_study_order
from brigade.studies.read_last_study_orders import LastStudyOrder


class DescribeLastStudyOrderTest(unittest.TestCase):
    def test_should_describe_the_run_and_outcome_of_the_last_order(self):
        # Arrange
        last_order = LastStudyOrder(run="r1", outcome="parked", started=datetime(2026, 10, 19, 8, 0, tzinfo=UTC))

        # Act
        described = describe_last_study_order(last_order)

        # Assert
        self.assertEqual(described, {"last_run": "r1", "outcome": "parked"})

    def test_should_describe_a_study_never_ordered_by_nothing(self):
        # Arrange
        never_ordered = None

        # Act
        described = describe_last_study_order(never_ordered)

        # Assert
        self.assertEqual(described, {"last_run": None, "outcome": None})
