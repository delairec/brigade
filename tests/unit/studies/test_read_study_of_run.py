import json
import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.studies.describe_milestone_report import describe_milestone_report
from brigade.studies.describe_task_report import describe_task_report
from brigade.studies.milestone_report_order import MilestoneReportOrder
from brigade.studies.read_study_of_run import read_study_of_run
from brigade.studies.task_report_order import TaskReportOrder
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime


class ReadStudyOfRunTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.run_directory = Path(directory.name) / "run"
        self.run_directory.mkdir()
        self.runtime = create_test_runtime(create_test_paths(Path(directory.name)))

    def record(self, document: dict) -> None:
        (self.run_directory / "study.json").write_text(json.dumps(document), encoding="utf-8")

    def test_should_read_the_report_of_the_task_the_run_records(self):
        # Arrange
        self.record(
            {
                "schema_version": 1,
                "study": "task-report",
                "project": "oak",
                "milestone": None,
                "task": {"project": "oak", "task": "B46", "wave": "oak_w4", "branch": "feature/B46-local-mode"},
            }
        )

        # Act
        study = read_study_of_run(self.runtime, self.run_directory)

        # Assert
        self.assertEqual(
            study,
            describe_task_report(
                TaskReportOrder(project="oak", task="B46", wave="oak_w4", branch="feature/B46-local-mode")
            ),
        )

    def test_should_read_the_report_of_the_milestone_the_run_records(self):
        # Arrange
        self.record(
            {
                "schema_version": 1,
                "study": "milestone-report",
                "project": "oak",
                "milestone": {
                    "project": "oak",
                    "milestone": "M6",
                    "branch": "integration/hardening",
                    "waves": ["oak_w2"],
                    "tasks": ["B17"],
                },
            }
        )

        # Act
        study = read_study_of_run(self.runtime, self.run_directory)

        # Assert
        self.assertEqual(
            study,
            describe_milestone_report(
                MilestoneReportOrder(
                    project="oak", milestone="M6", branch="integration/hardening", waves=("oak_w2",), tasks=("B17",)
                )
            ),
        )

    def test_should_refuse_a_run_that_records_no_study(self):
        # Act
        with self.assertRaises(BrigadeError) as raised:
            read_study_of_run(self.runtime, self.run_directory)

        # Assert
        self.assertEqual(str(raised.exception), "run is not a run of a study")
