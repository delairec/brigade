import json
import shlex
import unittest
from unittest.mock import ANY

from tests.cli.forgeless_wave_rehearser import (
    MILESTONE_BRANCH,
    ForgelessWaveRehearser,
    ForgelessWaveRehearserUnderNoAutoMerge,
)
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
                "task_merge_commands": [],
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


class BrigadeRehearsalOfAOneTaskWaveUnderNoAutoMergeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rehearser = ForgelessWaveRehearserUnderNoAutoMerge(ClassCleanupRegistrar(cls))
        cls.rehearser.run_brigade("request", "new", "shop", "Let the customer empty the cart")
        cls.rehearser.tick_until_the_task_is_verified()
        cls.tick_before_the_merge = cls.rehearser.run_brigade("tick", "--once")
        cls.shown_before_the_merge = cls.rehearser.run_brigade("wave", "show", "shop_w1", "--json")
        cls.command = cls.rehearser.read_the_command_named(cls.tick_before_the_merge.stdout)
        cls.files_on_the_branch_before_the_merge = cls.rehearser.project.run_git(
            "ls-tree", "--name-only", MILESTONE_BRANCH
        )
        cls.rehearser.project.run_git("checkout", "--quiet", "-b", "elsewhere")
        cls.rehearser.project.run_git(*shlex.split(cls.command)[1:])
        cls.rehearser.run_brigade("tick", "--once")
        cls.rehearser.list_finished_runs()

    def test_should_merge_nothing_before_the_user_runs_the_command(self):
        # Act
        files = self.files_on_the_branch_before_the_merge

        # Assert
        self.assertNotIn("delivered-S1.txt", files.splitlines())

    def test_should_merge_into_the_milestone_branch_whatever_branch_is_checked_out_at_the_clone(self):
        # Act
        delivered = self.rehearser.project.run_git("show", f"{MILESTONE_BRANCH}:delivered-S1.txt")

        # Assert
        self.assertEqual(delivered, "S1\n")

    def test_should_leave_the_branch_checked_out_at_the_clone_as_it_was(self):
        # Act
        files = self.rehearser.project.run_git("ls-tree", "--name-only", "elsewhere")

        # Assert
        self.assertNotIn("delivered-S1.txt", files.splitlines())

    def test_should_show_the_command_in_the_wave(self):
        # Act
        shown = json.loads(self.shown_before_the_merge.stdout)

        # Assert
        self.assertEqual(shown["task_merge_commands"], [self.command])

    def test_should_record_the_task_merged_and_close_its_wave_once_its_head_is_in_the_milestone_branch(self):
        # Act
        names = self.rehearser.list_event_names()
        states = self.rehearser.read_states_of("S1")

        # Assert
        self.assertIn("wave.closed", names)
        self.assertEqual(states[-1], "merged")
