import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from brigade.ledger.plan_lint_failed import PlanLintFailed
from brigade.ledger.write_event_line import write_event_line
from tests.unit.create_test_paths import create_test_paths


class PlanLintFailedTest(unittest.TestCase):
    def test_should_write_back_the_document_it_reads(self):
        # Arrange
        document = {"request": "req-1", "run": None}

        # Act
        written = PlanLintFailed.from_document(document).to_document()

        # Assert
        self.assertEqual(written, {"request": "req-1", "run": None})


class PlanLintFailedLineTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.paths = create_test_paths(Path(self.root.name))

    def tearDown(self):
        self.root.cleanup()

    def test_should_be_written_in_the_ledger_as_the_lint_failure_of_a_plan(self):
        # Arrange
        instant = datetime(2026, 10, 6, 9, 30, tzinfo=UTC)

        # Act
        line = write_event_line(self.paths, instant, PlanLintFailed(request="oak_r1", run="r1"))

        # Assert
        self.assertEqual(
            line,
            {
                "schema_version": 1,
                "ts": "2026-10-06T09:30:00Z",
                "event": "plan.lint_failed",
                "request": "oak_r1",
                "run": "r1",
            },
        )
