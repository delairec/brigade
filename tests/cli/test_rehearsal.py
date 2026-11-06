import json
import unittest
from unittest.mock import ANY

from tests.cli.wave_rehearser import ClassCleanupRegistrar, WaveRehearser


class BrigadeRehearsalOfAThreeTaskWaveOnTheFakeClientTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rehearser = WaveRehearser(ClassCleanupRegistrar(cls))
        cls.rehearser.run_brigade("request", "new", "shop", "Let the customer empty the cart")
        cls.rehearser.tick_until_the_milestone_is_reported()

    def test_should_close_the_wave_with_no_branch_once_its_three_tasks_are_merged(self):
        # Act
        completed = self.rehearser.run_brigade("wave", "show", "shop_w1", "--json")

        # Assert
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "wave": "shop_w1",
                "project": "shop",
                "branch": None,
                "started_at": ANY,
                "last_event": "wave.closed",
                "pull_request": None,
                "tasks": [
                    {"task": "S1", "state": "merged", "pull_request": ANY, "run": ANY, "reason": None},
                    {"task": "S2", "state": "merged", "pull_request": ANY, "run": ANY, "reason": None},
                    {"task": "S3", "state": "merged", "pull_request": ANY, "run": ANY, "reason": None},
                ],
            },
        )

    def test_should_merge_the_pull_request_of_a_task_from_its_own_branch_into_the_branch_of_its_milestone(self):
        # Arrange
        shown = json.loads(self.rehearser.run_brigade("wave", "show", "shop_w1", "--json").stdout)

        # Act
        pull_request = self.rehearser.read_pull_request(shown["tasks"][0]["pull_request"])

        # Assert
        self.assertEqual(
            pull_request,
            {
                "number": shown["tasks"][0]["pull_request"],
                "title": "feat: deliver S1 (@TASK.S1)",
                "body": ANY,
                "headRefName": "feature/S1-empty-the-cart-in-one-click",
                "baseRefName": "integration/empty-cart",
                "state": "MERGED",
                "mergedHead": ANY,
                "reviewDecision": None,
                "author": "octo-build",
            },
        )

    def test_should_open_the_pull_request_of_the_milestone_into_main_with_its_report_as_body(self):
        # Arrange
        report = self.rehearser.read_remote_file("integration/empty-cart", "corpus/milestones/M1-report.md")

        # Act
        pull_request = self.rehearser.read_pull_request(5)

        # Assert
        self.assertEqual(
            pull_request,
            {
                "number": 5,
                "title": "feat: deliver S1; deliver S2; deliver S3 (M1, @TASK.S1, @TASK.S2, @TASK.S3)",
                "body": report,
                "headRefName": "integration/empty-cart",
                "baseRefName": "main",
                "state": "OPEN",
                "reviewDecision": None,
                "author": "octo-build",
            },
        )

    def test_should_hold_the_milestone_reached_at_its_branch_once_its_pull_request_opens(self):
        # Act
        milestones = self.rehearser.read_remote_file("integration/empty-cart", "corpus/milestones.awawa")

        # Assert
        self.assertEqual(milestones, 'MILESTONE M1\n\tTITLE "Empty cart"\n\tSTATUS reached\n')

    def test_should_record_every_run_in_the_ledger(self):
        # Arrange
        self.rehearser.list_finished_runs()

        # Act
        completed = self.rehearser.run_brigade("ledger", "--json")

        # Assert
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "view": "overview",
                "events": {
                    "milestone.branch_cut": 1,
                    "milestone.created": 3,
                    "milestone.pr_described": 1,
                    "milestone.pr_opened": 1,
                    "milestone.reported": 1,
                    "order.done": 1,
                    "order.started": 1,
                    "pr.merged": 3,
                    "run.finished": 8,
                    "step.done": 3,
                    "task.pr_opened": 3,
                    "task.preflighted": 3,
                    "task.promoted": 3,
                    "task.state": 15,
                    "task.verdict": 3,
                    "wave.closed": 1,
                    "wave.started": 1,
                },
                "first": ANY,
                "last": ANY,
                "files": [ANY],
                "runs": {"outcomes": {"done": 8}, "error_classes": {}},
                "segments": {"outcomes": {"done": 8}, "error_classes": {}},
                "waves_started": ANY,
                "since": None,
                "skipped": [],
            },
        )
