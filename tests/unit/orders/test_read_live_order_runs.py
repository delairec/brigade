import json
import os
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from brigade.orders.live_order_run import LiveOrderRun
from brigade.orders.read_live_order_runs import read_live_order_runs

LIVE_RUN = "20261019T090000Z-aaaaaa"
ENDED_RUN = "20261018T090000Z-bbbbbb"
STARTED = datetime(2026, 10, 19, 9, 0, 3, tzinfo=UTC)


class ReadLiveOrderRunsTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.state_root = Path(directory.name)

    def write_order_record(self, run: str, recipe: str = "usage-report") -> None:
        run_directory = self.state_root / "runs" / run
        run_directory.mkdir(parents=True)
        (run_directory / "order.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "order": {"name": "nightly", "project": "shop"},
                    "recipe": {"name": recipe, "max_wall": 30, "steps": []},
                }
            ),
            encoding="utf-8",
        )
        os.utime(run_directory / "order.json", (STARTED.timestamp(), STARTED.timestamp()))

    def test_should_read_a_live_run_of_an_order_with_its_recipe_its_start_and_its_max_wall(self):
        # Arrange
        self.write_order_record(LIVE_RUN)
        self.write_order_record(ENDED_RUN)

        # Act
        live = read_live_order_runs(self.state_root, lambda run_directory: run_directory.name == LIVE_RUN)

        # Assert
        self.assertEqual(
            live,
            (LiveOrderRun(order="nightly", recipe="usage-report", run=LIVE_RUN, started=STARTED, max_wall=30),),
        )

    def test_should_leave_out_a_live_run_of_a_study(self):
        # Arrange
        self.write_order_record(LIVE_RUN, "study")

        # Act
        live = read_live_order_runs(self.state_root, lambda run_directory: run_directory.name == LIVE_RUN)

        # Assert
        self.assertEqual(live, ())
