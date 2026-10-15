import unittest
from datetime import UTC, datetime

from brigade.tick.build_snapshot import Snapshot


class SnapshotTest(unittest.TestCase):
    def test_should_carry_now_as_an_utc_instant_in_its_document(self):
        # Arrange
        snapshot = Snapshot(now=datetime(2026, 10, 6, 12, 0, 7, 250000, tzinfo=UTC))

        # Act
        document = snapshot.to_document()

        # Assert
        self.assertEqual(
            document, {"schema_version": 1, "now": "2026-10-06T12:00:07Z", "waves": [], "projects": [], "planned": []}
        )
