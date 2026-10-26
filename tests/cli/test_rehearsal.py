import json
import unittest
from unittest.mock import ANY

from tests.cli.wave_rehearser import ClassCleanupRegistrar, WaveRehearser


class BrigadeRehearsalOfAThreeTaskWaveOnTheFakeClientTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rehearser = WaveRehearser(ClassCleanupRegistrar(cls))
        cls.rehearser.run_brigade("request", "new", "shop", "Let the customer empty the cart")
        cls.rehearser.tick_until_the_wave_is_integrated()

    def test_should_merge_the_three_tasks_into_the_branch_of_the_wave(self):
        # Act
        completed = self.rehearser.run_brigade("wave", "show", "shop_w1", "--json")

        # Assert
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "wave": "shop_w1",
                "project": "shop",
                "branch": "integration/shop_w1",
                "started_at": ANY,
                "last_event": "wave.reported",
                "pull_request": ANY,
                "tasks": [
                    {"task": "S1", "state": "merged", "pull_request": ANY, "run": ANY, "reason": None},
                    {"task": "S2", "state": "merged", "pull_request": ANY, "run": ANY, "reason": None},
                    {"task": "S3", "state": "merged", "pull_request": ANY, "run": ANY, "reason": None},
                ],
            },
        )

    def test_should_open_the_integration_pull_request_the_wave_names(self):
        # Arrange
        shown = json.loads(self.rehearser.run_brigade("wave", "show", "shop_w1", "--json").stdout)

        # Act
        pull_request = self.rehearser.read_pull_request(shown["pull_request"])

        # Assert
        self.assertEqual(
            pull_request,
            {
                "number": shown["pull_request"],
                "title": "chore(wave): merge the wave shop_w1 into main",
                "body": "Integrates the wave shop_w1 of @PROJECT.shop into main: @TASK.S1, @TASK.S2, @TASK.S3.",
                "headRefName": "integration/shop_w1",
                "baseRefName": "main",
                "state": "OPEN",
                "reviewDecision": None,
                "author": "octo-build",
            },
        )

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
                    "milestone.created": 3,
                    "order.parked": 1,
                    "order.started": 1,
                    "pr.merged": 3,
                    "run.finished": 8,
                    "step.done": 1,
                    "step.failed": 1,
                    "task.pr_opened": 3,
                    "task.preflighted": 3,
                    "task.promoted": 3,
                    "task.rebased": 1,
                    "task.state": 16,
                    "task.verdict": 3,
                    "wave.pr_opened": 1,
                    "wave.reported": 1,
                    "wave.started": 1,
                },
                "first": ANY,
                "last": ANY,
                "files": [ANY],
                "runs": {"outcomes": {"done": 8}, "error_classes": {}},
                "segments": {"outcomes": {"done": 8}, "error_classes": {}},
                "skipped": [],
            },
        )
