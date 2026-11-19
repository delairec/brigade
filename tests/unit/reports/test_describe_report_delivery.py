import tempfile
import unittest
from pathlib import Path

from brigade.ledger.read_ledger import read_ledger
from brigade.reports.describe_report_delivery import describe_report_delivery
from tests.unit.commands.command_runtime import write_ledger


def write_delivery(root: Path) -> None:
    write_ledger(
        root,
        [
            {
                "schema_version": 1,
                "ts": "2026-10-01T08:00:00Z",
                "event": "milestone.branch_cut",
                "project": "oak",
                "milestone": "M4",
                "branch": "integration/roots",
                "login": None,
            },
            {
                "schema_version": 2,
                "ts": "2026-10-01T09:00:00Z",
                "event": "wave.started",
                "wave": "oak_w5",
                "project": "oak",
                "tasks": ["OK7"],
                "branch": "integration/roots",
            },
            {
                "schema_version": 2,
                "ts": "2026-10-01T09:30:00Z",
                "event": "wave.started",
                "wave": "elm_w5",
                "project": "elm",
                "tasks": ["OK7"],
                "branch": "integration/roots",
            },
            {
                "schema_version": 2,
                "ts": "2026-10-02T09:00:00Z",
                "event": "wave.started",
                "wave": "oak_w6",
                "project": "oak",
                "tasks": ["OK8"],
                "branch": "integration/roots",
            },
            {
                "schema_version": 2,
                "ts": "2026-10-02T10:00:00Z",
                "event": "wave.started",
                "wave": "oak_w7",
                "project": "oak",
                "tasks": ["OK9"],
            },
            {
                "schema_version": 1,
                "ts": "2026-10-02T11:00:00Z",
                "event": "task.pr_opened",
                "project": "oak",
                "task": "OK9",
                "wave": "oak_w7",
                "branch": "feature/OK9-bark",
                "pr": 52,
                "login": "bot",
            },
            {
                "schema_version": 1,
                "ts": "2026-10-02T12:00:00Z",
                "event": "task.reported",
                "project": "oak",
                "task": "OK9",
                "run": "20261002T120000Z-c3",
                "login": None,
            },
            {
                "schema_version": 1,
                "ts": "2026-10-03T08:00:00Z",
                "event": "milestone.reported",
                "project": "oak",
                "milestone": "M4",
                "run": "20261003T080000Z-a1",
                "login": None,
            },
            {
                "schema_version": 1,
                "ts": "2026-10-03T09:00:00Z",
                "event": "milestone.pr_opened",
                "project": "oak",
                "milestone": "M4",
                "pr": 57,
                "login": None,
            },
            {
                "schema_version": 1,
                "ts": "2026-10-04T09:00:00Z",
                "event": "wave.reported",
                "wave": "oak_w3",
                "run": None,
            },
            {
                "schema_version": 1,
                "ts": "2026-10-04T10:00:00Z",
                "event": "wave.pr_opened",
                "wave": "oak_w3",
                "pr": 31,
                "login": None,
            },
        ],
    )


def describe(root: Path, report: dict) -> dict:
    return describe_report_delivery(report, read_ledger(root / "state").entries)


class DescribeReportDeliveryOfAMilestoneReportTest(unittest.TestCase):
    def test_should_name_the_waves_of_its_milestone_its_pull_request_and_the_instant_it_was_reported(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_delivery(root)
        report = {
            "project": "oak",
            "fields": [{"name": "MILESTONE", "value": "M4"}, {"name": "PROJECT", "value": "oak"}],
        }

        # Act
        delivery = describe(root, report)

        # Assert
        self.assertEqual(
            delivery, {"waves": ["oak_w5", "oak_w6"], "pull_request": 57, "reported_at": "2026-10-03T08:00:00Z"}
        )


class DescribeReportDeliveryOfATaskReportTest(unittest.TestCase):
    def test_should_name_the_wave_of_its_task_its_pull_request_and_the_instant_it_was_reported(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_delivery(root)
        report = {
            "project": "oak",
            "fields": [{"name": "TASK", "value": "OK9"}, {"name": "PROJECT", "value": "oak"}],
        }

        # Act
        delivery = describe(root, report)

        # Assert
        self.assertEqual(delivery, {"waves": ["oak_w7"], "pull_request": 52, "reported_at": "2026-10-02T12:00:00Z"})


class DescribeReportDeliveryOfAWaveReportTest(unittest.TestCase):
    def test_should_name_its_wave_its_pull_request_and_the_instant_it_was_reported(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_delivery(root)
        report = {
            "project": "oak",
            "fields": [{"name": "WAVE", "value": "oak_w3"}, {"name": "PROJECT", "value": "oak"}],
        }

        # Act
        delivery = describe(root, report)

        # Assert
        self.assertEqual(delivery, {"waves": ["oak_w3"], "pull_request": 31, "reported_at": "2026-10-04T09:00:00Z"})


class DescribeReportDeliveryOfAMilestoneReportTheLedgerDoesNotRecordTest(unittest.TestCase):
    def test_should_name_no_wave_no_pull_request_and_no_instant(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        report = {
            "project": "oak",
            "fields": [{"name": "MILESTONE", "value": "M9"}, {"name": "PROJECT", "value": "oak"}],
        }

        # Act
        delivery = describe(root, report)

        # Assert
        self.assertEqual(delivery, {"waves": [], "pull_request": None, "reported_at": None})


class DescribeReportDeliveryOfAMilestoneWhoseBranchIsNotCutTest(unittest.TestCase):
    def test_should_name_none_of_the_waves_of_its_project_cut_from_no_branch(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_ledger(
            root,
            [
                {
                    "schema_version": 2,
                    "ts": "2026-10-01T09:00:00Z",
                    "event": "wave.started",
                    "wave": "oak_w2",
                    "project": "oak",
                    "tasks": ["OK1"],
                },
            ],
        )
        report = {
            "project": "oak",
            "fields": [{"name": "MILESTONE", "value": "M9"}, {"name": "PROJECT", "value": "oak"}],
        }

        # Act
        delivery = describe(root, report)

        # Assert
        self.assertEqual(delivery, {"waves": [], "pull_request": None, "reported_at": None})


class DescribeReportDeliveryBesideTheDeliveryOfAnotherProjectTest(unittest.TestCase):
    def test_should_keep_the_pull_request_and_the_instant_of_its_own_milestone(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_ledger(
            root,
            [
                {
                    "schema_version": 1,
                    "ts": "2026-10-03T08:00:00Z",
                    "event": "milestone.reported",
                    "project": "oak",
                    "milestone": "M4",
                    "run": "20261003T080000Z-a1",
                    "login": None,
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-03T09:00:00Z",
                    "event": "milestone.pr_opened",
                    "project": "oak",
                    "milestone": "M4",
                    "pr": 57,
                    "login": None,
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-04T08:00:00Z",
                    "event": "milestone.reported",
                    "project": "elm",
                    "milestone": "M4",
                    "run": "20261004T080000Z-b2",
                    "login": None,
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-04T09:00:00Z",
                    "event": "milestone.pr_opened",
                    "project": "elm",
                    "milestone": "M4",
                    "pr": 61,
                    "login": None,
                },
            ],
        )
        report = {
            "project": "oak",
            "fields": [{"name": "MILESTONE", "value": "M4"}, {"name": "PROJECT", "value": "oak"}],
        }

        # Act
        delivery = describe(root, report)

        # Assert
        self.assertEqual(delivery, {"waves": [], "pull_request": 57, "reported_at": "2026-10-03T08:00:00Z"})

    def test_should_keep_the_wave_the_pull_request_and_the_instant_of_its_own_task(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_ledger(
            root,
            [
                {
                    "schema_version": 2,
                    "ts": "2026-10-02T09:00:00Z",
                    "event": "wave.started",
                    "wave": "oak_w7",
                    "project": "oak",
                    "tasks": ["OK9"],
                },
                {
                    "schema_version": 2,
                    "ts": "2026-10-02T09:30:00Z",
                    "event": "wave.started",
                    "wave": "elm_w2",
                    "project": "elm",
                    "tasks": ["OK9"],
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-02T11:00:00Z",
                    "event": "task.pr_opened",
                    "project": "oak",
                    "task": "OK9",
                    "wave": "oak_w7",
                    "branch": "feature/OK9-bark",
                    "pr": 52,
                    "login": "bot",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-02T12:00:00Z",
                    "event": "task.reported",
                    "project": "oak",
                    "task": "OK9",
                    "run": "20261002T120000Z-c3",
                    "login": None,
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-03T11:00:00Z",
                    "event": "task.pr_opened",
                    "project": "elm",
                    "task": "OK9",
                    "wave": "elm_w2",
                    "branch": "feature/OK9-leaf",
                    "pr": 64,
                    "login": "bot",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-03T12:00:00Z",
                    "event": "task.reported",
                    "project": "elm",
                    "task": "OK9",
                    "run": "20261003T120000Z-d4",
                    "login": None,
                },
            ],
        )
        report = {
            "project": "oak",
            "fields": [{"name": "TASK", "value": "OK9"}, {"name": "PROJECT", "value": "oak"}],
        }

        # Act
        delivery = describe(root, report)

        # Assert
        self.assertEqual(delivery, {"waves": ["oak_w7"], "pull_request": 52, "reported_at": "2026-10-02T12:00:00Z"})


class DescribeReportDeliveryBesideTheDeliveryOfAnotherWaveTest(unittest.TestCase):
    def test_should_keep_the_pull_request_and_the_instant_of_its_own_wave(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_ledger(
            root,
            [
                {
                    "schema_version": 1,
                    "ts": "2026-10-04T09:00:00Z",
                    "event": "wave.reported",
                    "wave": "oak_w3",
                    "run": None,
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-04T10:00:00Z",
                    "event": "wave.pr_opened",
                    "wave": "oak_w3",
                    "pr": 31,
                    "login": None,
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-05T09:00:00Z",
                    "event": "wave.reported",
                    "wave": "oak_w4",
                    "run": None,
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-05T10:00:00Z",
                    "event": "wave.pr_opened",
                    "wave": "oak_w4",
                    "pr": 33,
                    "login": None,
                },
            ],
        )
        report = {
            "project": "oak",
            "fields": [{"name": "WAVE", "value": "oak_w3"}, {"name": "PROJECT", "value": "oak"}],
        }

        # Act
        delivery = describe(root, report)

        # Assert
        self.assertEqual(delivery, {"waves": ["oak_w3"], "pull_request": 31, "reported_at": "2026-10-04T09:00:00Z"})
