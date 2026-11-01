import json
import unittest
from unittest.mock import ANY

from tests.cli.wave_rehearser import ClassCleanupRegistrar, WaveRehearser


class BrigadeRehearsalOfAThreeTaskWaveOnTheFakeClientTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rehearser = WaveRehearser(ClassCleanupRegistrar(cls))
        cls.rehearser.move_the_head_of_a_branch_at_its_first_merge("integration/shop_w1")
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
                "last_event": "wave.closed",
                "pull_request": ANY,
                "tasks": [
                    {"task": "S1", "state": "merged", "pull_request": ANY, "run": ANY, "reason": None},
                    {"task": "S2", "state": "merged", "pull_request": ANY, "run": ANY, "reason": None},
                    {"task": "S3", "state": "merged", "pull_request": ANY, "run": ANY, "reason": None},
                ],
            },
        )

    def test_should_merge_the_pull_request_of_the_wave_into_the_branch_of_its_milestone(self):
        # Arrange
        shown = json.loads(self.rehearser.run_brigade("wave", "show", "shop_w1", "--json").stdout)

        # Act
        pull_request = self.rehearser.read_pull_request(shown["pull_request"])

        # Assert
        self.assertEqual(
            pull_request,
            {
                "number": shown["pull_request"],
                "title": "feat: deliver S1; deliver S2; deliver S3 (@TASK.S1, @TASK.S2, @TASK.S3)",
                "body": (
                    "Delivers the wave shop_w1 of the milestone M1 (Empty cart) into integration/empty-cart:"
                    " @TASK.S1, @TASK.S2, @TASK.S3.\n"
                    "\n"
                    "- @TASK.S1 — Empty the cart in one click (#2)\n"
                    "- @TASK.S2 — Confirm before emptying the cart (#5)\n"
                    "- @TASK.S3 — Count the emptied carts (#3)\n"
                    "- a push between the read and the merge"
                ),
                "headRefName": "integration/shop_w1",
                "baseRefName": "integration/empty-cart",
                "state": "MERGED",
                "mergedHead": ANY,
                "mergedCommits": ANY,
                "reviewDecision": None,
                "author": "octo-build",
            },
        )

    def test_should_leave_the_pull_request_of_the_wave_open_when_its_head_moved_since_the_read(self):
        # Act
        failed = self.rehearser.read_events_named("tick.action_failed")

        # Assert
        self.assertEqual(
            failed,
            [
                {
                    "schema_version": 1,
                    "ts": ANY,
                    "event": "tick.action_failed",
                    "action": "MergeWavePullRequest",
                    "project": "shop",
                    "wave": "shop_w1",
                    "task": None,
                    "error": ANY,
                }
            ],
        )
        self.assertRegex(
            failed[0]["error"],
            r"^gh pr merge \d+ --rebase --match-head-commit [0-9a-f]{40} exited 1: GraphQL: Head branch was modified\.",
        )

    def test_should_merge_the_pull_request_of_the_wave_at_its_new_head_after_the_refusal(self):
        # Arrange
        shown = json.loads(self.rehearser.run_brigade("wave", "show", "shop_w1", "--json").stdout)

        # Act
        pull_request = self.rehearser.read_pull_request(shown["pull_request"])

        # Assert
        self.assertEqual(pull_request["mergedHead"], self.rehearser.read_branch_head("integration/shop_w1"))

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
                    "order.parked": 1,
                    "order.started": 1,
                    "pr.merged": 3,
                    "run.finished": 8,
                    "step.done": 1,
                    "step.failed": 1,
                    "task.pr_opened": 3,
                    "task.preflighted": 3,
                    "task.promoted": 3,
                    "task.state": 15,
                    "task.verdict": 3,
                    "tick.action_failed": 1,
                    "wave.closed": 1,
                    "wave.merged": 1,
                    "wave.pr_described": 3,
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
