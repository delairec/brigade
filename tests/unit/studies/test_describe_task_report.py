import unittest

from brigade.studies.convert_study import Study
from brigade.studies.describe_task_report import describe_task_report
from brigade.studies.task_report_order import TaskReportOrder


class DescribeTaskReportTest(unittest.TestCase):
    def test_should_collect_the_events_of_the_wave_of_the_task_and_the_task_and_changes_of_its_branch(self):
        # Arrange
        order = TaskReportOrder(project="oak", task="B46", wave="oak_w4", branch="feature/B46-local-mode")

        # Act
        study = describe_task_report(order)

        # Assert
        self.assertEqual(
            study,
            Study(
                name="task-report",
                project="oak",
                question=(
                    "Complete the report of the task B46: what happened, why it stopped if parked or failed,"
                    " how a tester checks each manual test, and which changes are worth reading by sampling."
                ),
                collectors=(
                    "ledger wave=oak_w4",
                    "pr-list state=all",
                    "corpus ref=feature/B46-local-mode entities=@TASK.B46",
                    "git-diff-stat to=feature/B46-local-mode",
                ),
                slot="report",
                every=None,
                output="entity:REPORT",
                answer_type="REPORT",
                status="active",
                task=order,
            ),
        )
