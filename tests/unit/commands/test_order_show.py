import tempfile
import unittest
from argparse import Namespace
from datetime import UTC, datetime
from pathlib import Path

from brigade.commands.order_show import COMMAND
from brigade.ledger.append_event import append_event
from brigade.ledger.order_done import OrderDone
from brigade.ledger.order_parked import OrderParked
from brigade.ledger.order_started import OrderStarted
from tests.unit.commands.command_runtime import create_corpus_double, write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

NIGHTLY_ORDER = (
    ("RECIPE", "usage-report"),
    ("PROJECT", "@PROJECT.oak"),
    ("TEXT", "the cost of the review"),
    ("PARAM", "pull_request=12"),
    ("EVERY", "daily@07:00"),
    ("STATUS", "active"),
)
MONDAY = datetime(2026, 10, 19, 7, 0, tzinfo=UTC)
TUESDAY = datetime(2026, 10, 20, 7, 0, tzinfo=UTC)
WEDNESDAY = datetime(2026, 10, 21, 7, 0, tzinfo=UTC)
NIGHTLY_SHOWN = {
    "schema_version": 1,
    "order": {
        "name": "nightly",
        "recipe": "usage-report",
        "project": "oak",
        "text": "the cost of the review",
        "params": ["pull_request=12"],
        "every": "daily@07:00",
        "status": "active",
    },
    "runs": [
        {"run": "20261019T070000Z-aaaaaa", "started": "2026-10-19T07:00:00Z", "outcome": "done"},
        {"run": "20261020T070000Z-bbbbbb", "started": "2026-10-20T07:00:00Z", "outcome": "parked"},
        {"run": "20261021T070000Z-cccccc", "started": "2026-10-21T07:00:00Z", "outcome": "running"},
    ],
}


class OrderShowTest(unittest.TestCase):
    def test_should_print_the_order_with_each_of_its_runs_and_their_outcome(self):
        # Arrange
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        write_operational_corpus(root)
        paths = create_test_paths(root)
        runtime = create_test_runtime(paths, run_process=create_corpus_double({"ORDER": {"nightly": NIGHTLY_ORDER}}))
        monday_run = OrderStarted(project="oak", kind="usage-report", order="nightly", run="20261019T070000Z-aaaaaa")
        append_event(paths, MONDAY, monday_run)
        append_event(
            paths, MONDAY, OrderStarted(project=None, kind="cleanup", order="cleanup", run="20261019T070000Z-dddddd")
        )
        append_event(
            paths, MONDAY, OrderDone(project="oak", kind="usage-report", order="nightly", run="20261019T070000Z-aaaaaa")
        )
        append_event(
            paths,
            TUESDAY,
            OrderStarted(project="oak", kind="usage-report", order="nightly", run="20261020T070000Z-bbbbbb"),
        )
        append_event(
            paths,
            TUESDAY,
            OrderParked(
                project="oak",
                kind="usage-report",
                order="nightly",
                run="20261020T070000Z-bbbbbb",
                step="1-gate",
                reason="red",
            ),
        )
        append_event(
            paths,
            WEDNESDAY,
            OrderStarted(project="oak", kind="usage-report", order="nightly", run="20261021T070000Z-cccccc"),
        )

        # Act
        document = COMMAND.run(Namespace(name="nightly"), runtime)

        # Assert
        self.assertEqual(document, NIGHTLY_SHOWN)

    def test_should_print_the_order_then_one_line_per_run(self):
        # Act
        text = COMMAND.render_text(NIGHTLY_SHOWN)

        # Assert
        self.assertEqual(
            text,
            "@ORDER.nightly: recipe usage-report, project oak, every daily@07:00, active\n"
            "run                      started               outcome\n"
            "20261019T070000Z-aaaaaa  2026-10-19T07:00:00Z  done\n"
            "20261020T070000Z-bbbbbb  2026-10-20T07:00:00Z  parked\n"
            "20261021T070000Z-cccccc  2026-10-21T07:00:00Z  running",
        )
