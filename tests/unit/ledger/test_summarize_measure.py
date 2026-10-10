import unittest
from dataclasses import replace
from datetime import UTC, datetime

from brigade.ledger.finished_run import FinishedRun
from brigade.ledger.run_finished import RunFinished
from brigade.ledger.summarize_measure import summarize_measure

SEGMENT = RunFinished(
    run="20261010T090000Z-b86a01",
    segment=1,
    procedure="awawa-task",
    slot="build",
    role="builder",
    client="claude-code",
    project="tidepool",
    session=None,
    main_steps=None,
    total_steps=None,
    duration_ms=1000,
    usage=None,
    outcome="done",
    error_class=None,
    exit=0,
    wave=None,
    task=None,
    nulls={},
)
FINISHED_AT = datetime(2026, 10, 10, tzinfo=UTC)


class SummarizeMeasureTest(unittest.TestCase):
    def test_should_summarize_the_runs_with_their_partial_sums_beside_the_segments(self):
        # Arrange
        partial_run = FinishedRun(
            run="20261010T090000Z-b86a01",
            finished_at=FINISHED_AT,
            segments=(SEGMENT, replace(SEGMENT, segment=2, main_steps=30)),
        )
        measured_run = FinishedRun(
            run="20261010T090000Z-b86a02",
            finished_at=FINISHED_AT,
            segments=(replace(SEGMENT, main_steps=50), replace(SEGMENT, segment=2, main_steps=25)),
        )
        unmeasured_run = FinishedRun(run="20261010T090000Z-b86a03", finished_at=FINISHED_AT, segments=(SEGMENT,))

        # Act
        summary = summarize_measure([partial_run, measured_run, unmeasured_run], "main_steps")

        # Assert
        self.assertEqual(
            summary,
            {
                "runs": {"measured": 2, "partial": 1, "unmeasured": 1, "p50": 30, "p90": 75},
                "segments": {"measured": 3, "unmeasured": 2, "p50": 30, "p90": 50},
            },
        )
