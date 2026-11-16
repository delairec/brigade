import tempfile
import unittest
from pathlib import Path

from brigade.ledger.append_event import append_event
from brigade.ledger.order_done import OrderDone
from brigade.ledger.order_parked import OrderParked
from brigade.ledger.order_started import OrderStarted
from brigade.orders.convert_order import Order
from brigade.orders.find_parked_order_run import NO_PARKED_RUN, find_parked_order_run
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

RUN_ID = "20261019T080000Z-aaaaaa"
ORDER = Order(
    name="nightly",
    recipe="usage-report",
    project="shop",
    text=None,
    params=(),
    every=None,
    output=None,
    status="active",
)
STARTED = OrderStarted(project="shop", kind="usage-report", order="nightly", run=RUN_ID)
PARKED = OrderParked(
    project="shop", kind="usage-report", order="nightly", run=RUN_ID, step="1-gate", reason="the gate step failed"
)
DONE = OrderDone(project="shop", kind="usage-report", order="nightly", run=RUN_ID)


class FindParkedOrderRunTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.runtime = create_test_runtime(create_test_paths(Path(directory.name)))

    def _record(self, *events):
        for event in events:
            append_event(self.runtime.paths, self.runtime.now, event)

    def test_should_find_the_run_whose_last_event_parked_it(self):
        # Arrange
        self._record(STARTED, PARKED)

        # Act
        run = find_parked_order_run(self.runtime, ORDER)

        # Assert
        self.assertEqual(run, RUN_ID)

    def test_should_find_no_parked_run_when_the_last_event_started_a_run(self):
        # Arrange
        self._record(STARTED, PARKED, STARTED)

        # Act
        run = find_parked_order_run(self.runtime, ORDER)

        # Assert
        self.assertIs(run, NO_PARKED_RUN)

    def test_should_find_no_parked_run_when_the_last_event_finished_a_run(self):
        # Arrange
        self._record(STARTED, PARKED, STARTED, DONE)

        # Act
        run = find_parked_order_run(self.runtime, ORDER)

        # Assert
        self.assertIs(run, NO_PARKED_RUN)
