import unittest
from datetime import UTC, datetime

from brigade.tick.build_snapshot import Snapshot
from brigade.tick.plan import plan


class Plan(unittest.TestCase):
    def test_should_plan_no_action_yet(self):
        # Arrange
        snapshot = Snapshot(now=datetime(2026, 10, 6, 12, 0, tzinfo=UTC))

        # Act
        actions = plan(snapshot)

        # Assert
        self.assertEqual(actions, ())
