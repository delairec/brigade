import json
import tempfile
import unittest
from pathlib import Path

from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.order_started import OrderStarted
from brigade.ledger.read_ledger import read_ledger
from brigade.orders.convert_order import Order
from brigade.orders.start_order_run import start_order_run
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import FIXED_NOW, create_test_runtime

RUN_ID = "20261019T090000Z-aaaaaa"
NIGHTLY = Order(
    name="nightly",
    recipe="usage-report",
    project="shop",
    text="the cost",
    params=("pull_request=12",),
    every=None,
    status="active",
)


class StartOrderRunTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.runtime = create_test_runtime(create_test_paths(Path(directory.name)))

    def test_should_record_the_order_in_its_run_directory(self):
        # Act
        start_order_run(self.runtime, NIGHTLY, RUN_ID)

        # Assert
        record = self.runtime.paths.state_root / "runs" / RUN_ID / "order.json"
        self.assertEqual(
            json.loads(record.read_text(encoding="utf-8")),
            {
                "schema_version": 1,
                "order": {
                    "name": "nightly",
                    "recipe": "usage-report",
                    "project": "shop",
                    "text": "the cost",
                    "params": ["pull_request=12"],
                    "every": None,
                    "status": "active",
                },
            },
        )

    def test_should_record_the_start_of_the_run_under_the_name_of_its_recipe(self):
        # Act
        start_order_run(self.runtime, NIGHTLY, RUN_ID)

        # Assert
        self.assertEqual(
            read_ledger(self.runtime.paths.state_root).entries,
            (
                LedgerEntry(
                    instant=FIXED_NOW,
                    event=OrderStarted(project="shop", kind="usage-report", order="nightly", run=RUN_ID),
                ),
            ),
        )
