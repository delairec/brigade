import unittest

from brigade.orders.convert_order import Order
from brigade.studies.convert_study import Study
from brigade.studies.describe_milestone_report import describe_milestone_report
from brigade.studies.describe_study_order import describe_study_order
from brigade.studies.describe_task_report import describe_task_report
from brigade.studies.milestone_report_order import MilestoneReportOrder
from brigade.studies.task_report_order import TaskReportOrder

TREES = Study(
    name="trees",
    project="oak",
    question="Which trees grow?",
    collectors=("ledger",),
    slot="study",
    every="7d",
    output="inbox",
    answer_type="FINDING",
    status="active",
)


class DescribeStudyOrderTest(unittest.TestCase):
    def test_should_describe_a_study_as_an_order_of_the_recipe_study(self):
        # Act
        order = describe_study_order(TREES)

        # Assert
        self.assertEqual(
            order,
            Order(
                name="trees",
                recipe="study",
                project="oak",
                text=None,
                params=(),
                every="7d",
                output="inbox",
                status="active",
            ),
        )

    def test_should_carry_the_milestone_of_a_milestone_report_as_its_argument(self):
        # Arrange
        report = describe_milestone_report(
            MilestoneReportOrder(
                project="oak", milestone="M6", branch="integration/hardening", waves=("oak_w2",), tasks=("B17",)
            )
        )

        # Act
        order = describe_study_order(report)

        # Assert
        self.assertEqual(
            order.params,
            (
                (
                    'milestone={"project": "oak", "milestone": "M6", "branch": "integration/hardening",'
                    ' "waves": ["oak_w2"], "tasks": ["B17"], "reads_pull_requests": true}'
                ),
            ),
        )

    def test_should_carry_the_task_of_a_task_report_as_its_argument(self):
        # Arrange
        report = describe_task_report(
            TaskReportOrder(project="oak", task="B46", wave="oak_w4", branch="feature/B46-local-mode")
        )

        # Act
        order = describe_study_order(report)

        # Assert
        self.assertEqual(
            order.params,
            ('task={"project": "oak", "task": "B46", "wave": "oak_w4", "branch": "feature/B46-local-mode"}',),
        )
