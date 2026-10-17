import unittest
from datetime import UTC, datetime

from brigade.ledger.finished_run import FinishedRun
from brigade.ledger.group_runs import group_runs
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.run_finished import RunFinished
from brigade.ledger.wave_started import WaveStarted

CUT_SEGMENT = RunFinished(
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
    outcome="wall_limit",
    error_class=None,
    exit=None,
    wave="tp/16",
    task="TP146",
    nulls={},
)
RESUMED_SEGMENT = RunFinished(
    run="20261010T090000Z-b86a01",
    segment=2,
    procedure="awawa-task",
    slot="build",
    role="builder",
    client="claude-code",
    project="tidepool",
    session=None,
    main_steps=30,
    total_steps=None,
    duration_ms=1000,
    usage=None,
    outcome="done",
    error_class=None,
    exit=0,
    wave="tp/16",
    task="TP146",
    nulls={},
)
OTHER_RUN = RunFinished(
    run="20261010T093000Z-b86a02",
    segment=1,
    procedure="awawa-pr-review",
    slot="review",
    role="remi",
    client="claude-code",
    project="tidepool",
    session=None,
    main_steps=12,
    total_steps=None,
    duration_ms=1000,
    usage=None,
    outcome="done",
    error_class=None,
    exit=0,
    wave="tp/16",
    task="TP146",
    nulls={},
)


class GroupRunsTest(unittest.TestCase):
    def test_should_gather_the_segments_of_a_run_and_date_it_by_its_last_one(self):
        # Arrange
        entries = [
            LedgerEntry(
                datetime(2026, 10, 10, 9, tzinfo=UTC),
                WaveStarted(wave="tp/16", project="tidepool", branch="integration/M4-tides", tasks=("T7",)),
            ),
            LedgerEntry(datetime(2026, 10, 10, 10, tzinfo=UTC), CUT_SEGMENT),
            LedgerEntry(datetime(2026, 10, 10, 11, tzinfo=UTC), OTHER_RUN),
            LedgerEntry(datetime(2026, 10, 10, 12, tzinfo=UTC), RESUMED_SEGMENT),
        ]

        # Act
        runs = group_runs(entries)

        # Assert
        self.assertEqual(
            runs,
            [
                FinishedRun(
                    run="20261010T093000Z-b86a02",
                    finished_at=datetime(2026, 10, 10, 11, tzinfo=UTC),
                    segments=(OTHER_RUN,),
                ),
                FinishedRun(
                    run="20261010T090000Z-b86a01",
                    finished_at=datetime(2026, 10, 10, 12, tzinfo=UTC),
                    segments=(CUT_SEGMENT, RESUMED_SEGMENT),
                ),
            ],
        )
