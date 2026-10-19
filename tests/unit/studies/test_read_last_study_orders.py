import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from brigade.ledger.append_event import append_event
from brigade.ledger.order_done import OrderDone
from brigade.ledger.order_parked import OrderParked
from brigade.ledger.order_started import OrderStarted
from brigade.ledger.step_done import StepDone
from brigade.studies.read_last_study_orders import LastStudyOrder, read_last_study_orders
from tests.unit.create_scripted_runtime import create_scripted_runtime
from tests.unit.scripted_processes import ScriptedProcesses


class ReadLastStudyOrdersTest(unittest.TestCase):
    def test_should_read_the_last_order_of_each_study_with_the_instant_it_started(self):
        # Arrange
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        paths = create_scripted_runtime(Path(directory.name), ScriptedProcesses()).paths
        append_event(
            paths,
            datetime(2026, 10, 18, 7, 0, tzinfo=UTC),
            OrderStarted(project=None, kind="study", order="trees", run="r1"),
        )
        append_event(paths, datetime(2026, 10, 18, 7, 1, tzinfo=UTC), StepDone(kind="study", run="r1", step="collect"))
        append_event(
            paths,
            datetime(2026, 10, 18, 7, 2, tzinfo=UTC),
            OrderParked(project=None, kind="study", order="trees", run="r1", step="judge", reason="quota"),
        )
        append_event(
            paths,
            datetime(2026, 10, 19, 7, 0, tzinfo=UTC),
            OrderStarted(project=None, kind="study", order="ash", run="r2"),
        )
        append_event(
            paths,
            datetime(2026, 10, 19, 7, 5, tzinfo=UTC),
            OrderDone(project=None, kind="study", order="ash", run="r2"),
        )
        append_event(
            paths,
            datetime(2026, 10, 19, 8, 0, tzinfo=UTC),
            OrderDone(project="oak", kind="task", order="B12", run="r3"),
        )

        # Act
        last_orders = read_last_study_orders(paths.state_root)

        # Assert
        self.assertEqual(
            last_orders,
            {
                "trees": LastStudyOrder(run="r1", outcome="parked", started=datetime(2026, 10, 18, 7, 0, tzinfo=UTC)),
                "ash": LastStudyOrder(run="r2", outcome="done", started=datetime(2026, 10, 19, 7, 0, tzinfo=UTC)),
            },
        )

    def test_should_read_no_start_for_an_order_whose_start_the_ledger_lost(self):
        # Arrange
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        paths = create_scripted_runtime(Path(directory.name), ScriptedProcesses()).paths
        append_event(
            paths,
            datetime(2026, 10, 19, 7, 5, tzinfo=UTC),
            OrderDone(project=None, kind="study", order="ash", run="r2"),
        )

        # Act
        last_orders = read_last_study_orders(paths.state_root)

        # Assert
        self.assertEqual(last_orders, {"ash": LastStudyOrder(run="r2", outcome="done", started=None)})
