import signal
import tempfile
import unittest
from pathlib import Path

from brigade.inbox.read_inbox import read_inbox
from brigade.ledger.order_parked import OrderParked
from brigade.ledger.read_ledger import read_ledger
from brigade.orders.convert_order import Order
from brigade.orders.start_order_run import start_order_run
from brigade.orders.stop_order_run import stop_order_run
from brigade.tick.actions import StopOrderRun
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import FIXED_NOW, create_test_runtime

RUN_ID = "20261019T080000Z-aaaaaa"
NIGHTLY = Order(
    name="nightly",
    recipe="usage-report",
    project="shop",
    text=None,
    params=(),
    every="24h",
    output=None,
    status="active",
)
USAGE_REPORT = {"name": "usage-report", "max_wall": 30, "steps": [{"kind": "command"}, {"kind": "judge"}]}
REASON = "the run passed the max_wall of 30 minutes of the recipe usage-report"


class StopOrderRunTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.runtime = create_test_runtime(create_test_paths(Path(directory.name)))
        start_order_run(self.runtime, NIGHTLY, USAGE_REPORT, RUN_ID)
        run_directory = self.runtime.paths.state_root / "runs" / RUN_ID
        (run_directory / "steps").mkdir()
        (run_directory / "steps" / "1-command.json").write_text("{}", encoding="utf-8")
        (run_directory / "pid").write_text("4242 100 boot\n", encoding="utf-8")
        self.signals = []

    def test_should_stop_the_process_of_the_run_and_park_its_order_at_its_first_undone_step(self):
        # Act
        stop_order_run(
            self.runtime,
            StopOrderRun(order="nightly", run=RUN_ID, reason=REASON),
            lambda pid, sent: self.signals.append((pid, sent)),
        )

        # Assert
        self.assertEqual(self.signals, [(4242, signal.SIGTERM)])
        self.assertEqual(
            read_ledger(self.runtime.paths.state_root).entries[-2].event,
            OrderParked(
                project="shop", kind="usage-report", order="nightly", run=RUN_ID, step="2-judge", reason=REASON
            ),
        )

    def test_should_park_its_order_at_its_last_step_when_every_step_file_is_written(self):
        # Arrange
        (self.runtime.paths.state_root / "runs" / RUN_ID / "steps" / "2-judge.json").write_text("{}", encoding="utf-8")

        # Act
        stop_order_run(self.runtime, StopOrderRun(order="nightly", run=RUN_ID, reason=REASON), self.signals_sent)

        # Assert
        self.assertEqual(read_ledger(self.runtime.paths.state_root).entries[-2].event.step, "2-judge")

    def test_should_signal_in_the_inbox_the_order_it_parked(self):
        # Act
        stop_order_run(self.runtime, StopOrderRun(order="nightly", run=RUN_ID, reason=REASON), self.signals_sent)

        # Assert
        self.assertEqual(
            read_inbox(self.runtime.paths.state_root, FIXED_NOW)[0].fingerprint,
            "order_parked:nightly:20261019T080000Z-aaaaaa",
        )

    def signals_sent(self, pid: int, sent: int) -> None:
        self.signals.append((pid, sent))
