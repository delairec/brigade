import json
import unittest
from unittest.mock import ANY

from tests.cli.forgeless_wave_rehearser import MILESTONE_BRANCH, ForgelessWaveRehearser
from tests.cli.wave_rehearser import ClassCleanupRegistrar


class BrigadeRehearsalOfAOneTaskWaveOfAProjectWithoutAForgeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rehearser = ForgelessWaveRehearser(ClassCleanupRegistrar(cls))
        cls.rehearser.run_brigade("request", "new", "shop", "Let the customer empty the cart")
        cls.rehearser.tick_until_the_milestone_is_reported()
        cls.tick_before_the_merge = cls.rehearser.run_brigade("tick", "--once")
        cls.shown_before_the_merge = cls.rehearser.run_brigade("wave", "show", "shop_w1", "--json")
        cls.delivered_on_the_branch = cls.rehearser.project.run_git("show", f"{MILESTONE_BRANCH}:delivered-S1.txt")
        cls.merge_command = f"git -C {cls.rehearser.project.path} merge {MILESTONE_BRANCH}"
        cls.rehearser.project.run_git("merge", "--quiet", MILESTONE_BRANCH)
        cls.rehearser.run_brigade("tick", "--once")

    def test_should_record_the_preflight_the_verdict_the_merge_and_the_close_of_its_wave(self):
        # Act
        names = self.rehearser.list_event_names()

        # Assert
        for name in ("task.preflighted", "task.verdict", "pr.merged", "wave.closed"):
            with self.subTest(event=name):
                self.assertIn(name, names)

    def test_should_record_the_merge_of_the_task_with_no_pull_request(self):
        # Act
        merged = self.rehearser.find_event("pr.merged")

        # Assert
        self.assertNotIn("pr", merged)

    def test_should_merge_the_task_into_the_branch_of_its_milestone(self):
        # Act
        delivered = self.delivered_on_the_branch

        # Assert
        self.assertEqual(delivered, "S1\n")

    def test_should_show_the_wave_closed_with_the_command_merging_its_milestone(self):
        # Act
        shown = json.loads(self.shown_before_the_merge.stdout)

        # Assert
        self.assertEqual(
            shown,
            {
                "schema_version": 1,
                "wave": "shop_w1",
                "project": "shop",
                "branch": None,
                "started_at": ANY,
                "last_event": "wave.closed",
                "pull_request": None,
                "tasks": [{"task": "S1", "state": "merged", "pull_request": None, "run": ANY, "reason": None}],
                "merge_command": self.merge_command,
            },
        )

    def test_should_name_the_command_in_the_text_of_the_tick(self):
        # Act
        text = self.tick_before_the_merge.stdout

        # Assert
        self.assertIn(f"to merge: {self.merge_command}\n", text)

    def test_should_close_the_milestone_with_no_pull_request_once_the_user_merged_its_branch(self):
        # Act
        closed = self.rehearser.find_event("milestone.closed")

        # Assert
        self.assertEqual(
            closed,
            {"schema_version": 1, "ts": ANY, "event": "milestone.closed", "project": "shop", "milestone": "M1"},
        )
