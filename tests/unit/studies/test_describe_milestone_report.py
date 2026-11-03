import unittest

from brigade.studies.convert_study import Study
from brigade.studies.describe_milestone_report import describe_milestone_report
from brigade.studies.milestone_report_order import MilestoneReportOrder


class DescribeMilestoneReportTest(unittest.TestCase):
    def test_should_collect_the_events_of_each_wave_and_the_tasks_and_changes_of_the_milestone_branch(self):
        # Arrange
        order = MilestoneReportOrder(
            project="oak",
            milestone="M6",
            branch="integration/hardening",
            waves=("oak_w2", "oak_w3"),
            tasks=("B17", "B21"),
        )

        # Act
        study = describe_milestone_report(order)

        # Assert
        self.assertEqual(
            study,
            Study(
                name="milestone-report",
                project="oak",
                question=(
                    "Complete the report of the milestone M6: what happened, why each parked or failed task stopped,"
                    " how a tester checks each manual test, and which changes are worth reading by sampling."
                ),
                collectors=(
                    "ledger wave=oak_w2",
                    "ledger wave=oak_w3",
                    "pr-list state=all",
                    "corpus ref=integration/hardening entities=@TASK.B17,@TASK.B21",
                    "git-diff-stat to=integration/hardening",
                ),
                slot="report",
                every=None,
                output="entity:REPORT",
                answer_type="REPORT",
                status="active",
                milestone=order,
            ),
        )
