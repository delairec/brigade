import tempfile
import unittest
from pathlib import Path

from brigade.inbox.read_inbox import Signal, read_inbox
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.order_parked import OrderParked
from brigade.ledger.read_ledger import read_ledger
from brigade.orders.park_order import park_order
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import FIXED_NOW, create_test_runtime

RUN_ID = "20261019T080000Z-aaaaaa"
PARKED = OrderParked(
    project="shop", kind="usage-report", order="nightly", run=RUN_ID, step="1-gate", reason="the gate step failed"
)


class ParkOrderTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.runtime = create_test_runtime(create_test_paths(Path(directory.name)))

    def test_should_record_the_order_parked_in_the_ledger(self):
        # Act
        park_order(self.runtime, PARKED)

        # Assert
        self.assertEqual(read_ledger(self.runtime.paths.state_root).entries[0], LedgerEntry(FIXED_NOW, PARKED))

    def test_should_signal_the_order_parked_in_the_inbox(self):
        # Act
        park_order(self.runtime, PARKED)

        # Assert
        self.assertEqual(
            read_inbox(self.runtime.paths.state_root, FIXED_NOW),
            (
                Signal(
                    id="ba0a47c572a8eb52a118e7f55afcb45794f31c7a79126cfebe29079f856cef80",
                    fingerprint="order_parked:nightly:20261019T080000Z-aaaaaa",
                    kind="order_parked",
                    project="shop",
                    count=1,
                    age_s=0,
                    status="new",
                    evidence={
                        "order": "nightly",
                        "recipe": "usage-report",
                        "run": "20261019T080000Z-aaaaaa",
                        "step": "1-gate",
                        "reason": "the gate step failed",
                    },
                ),
            ),
        )
