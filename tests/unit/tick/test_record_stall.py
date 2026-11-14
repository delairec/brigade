import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from brigade.inbox.read_inbox import Signal, read_inbox
from brigade.tick.actions import SignalStall
from brigade.tick.record_stall import record_stall
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

FIRST_TICK = datetime(2026, 10, 19, 9, 0, tzinfo=UTC)
NEXT_TICK = datetime(2026, 10, 19, 9, 5, tzinfo=UTC)
STALL_OF_S3 = SignalStall(
    project="shop", wave="shop_w1", task="S3", last_action=datetime(2026, 10, 19, 7, 30, tzinfo=UTC)
)


class RecordStallTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.paths = create_test_paths(Path(directory.name))

    def test_should_record_the_stall_as_a_signal_of_its_own_kind_named_by_the_project_the_wave_and_the_task(self):
        # Act
        record_stall(create_test_runtime(self.paths, now=FIRST_TICK), STALL_OF_S3)

        # Assert
        self.assertEqual(
            read_inbox(self.paths.state_root, FIRST_TICK),
            (
                Signal(
                    id="cf683415b22154f89c71aaa3d08b9bbde22ff9342d038162680a56a5f8322af1",
                    fingerprint="stall:shop:shop_w1:S3",
                    kind="stall",
                    project="shop",
                    count=1,
                    age_s=0,
                    status="new",
                    evidence={"wave": "shop_w1", "task": "S3", "last_action": "2026-10-19T07:30:00Z"},
                ),
            ),
        )

    def test_should_fold_the_same_stall_recorded_at_the_next_tick_into_its_signal(self):
        # Arrange
        record_stall(create_test_runtime(self.paths, now=FIRST_TICK), STALL_OF_S3)

        # Act
        record_stall(create_test_runtime(self.paths, now=NEXT_TICK), STALL_OF_S3)

        # Assert
        self.assertEqual(
            read_inbox(self.paths.state_root, NEXT_TICK),
            (
                Signal(
                    id="cf683415b22154f89c71aaa3d08b9bbde22ff9342d038162680a56a5f8322af1",
                    fingerprint="stall:shop:shop_w1:S3",
                    kind="stall",
                    project="shop",
                    count=2,
                    age_s=300,
                    status="new",
                    evidence={"wave": "shop_w1", "task": "S3", "last_action": "2026-10-19T07:30:00Z"},
                ),
            ),
        )
