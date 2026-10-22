import unittest

from brigade.ledger.wave_started import WaveStarted
from brigade.studies.convert_study import Study
from brigade.studies.describe_wave_report import describe_wave_report


class DescribeWaveReportTest(unittest.TestCase):
    def test_should_collect_the_events_the_pull_requests_the_tasks_and_the_changes_of_the_wave(self):
        # Arrange
        started = WaveStarted(wave="oak_w2", project="oak", branch="integration/oak_w2", tasks=("B17", "B21"))

        # Act
        study = describe_wave_report(started)

        # Assert
        self.assertEqual(
            study,
            Study(
                name="wave-report",
                project="oak",
                question=(
                    "Complete the report of the wave oak_w2: what happened, why each parked or failed task stopped,"
                    " how a tester checks each manual test, and which changes are worth reading by sampling."
                ),
                collectors=(
                    "ledger wave=oak_w2",
                    "pr-list state=all",
                    "corpus ref=integration/oak_w2 entities=@TASK.B17,@TASK.B21",
                    "git-diff-stat to=integration/oak_w2",
                ),
                slot="report",
                every=None,
                output="entity:REPORT",
                answer_type="REPORT",
                status="active",
                wave="oak_w2",
            ),
        )
