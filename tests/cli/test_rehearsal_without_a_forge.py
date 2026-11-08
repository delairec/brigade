import json
import unittest
from unittest.mock import ANY

from tests.cli.wave_rehearser import AWAIT_THE_RELEASE, READ_THE_BRIEF, ClassCleanupRegistrar, WaveRehearser

MILESTONE_BRANCH = "integration/empty-cart"
ONE_TASK_PLAN = (
    'MILESTONE M1\n\tTITLE "Empty cart"\n\tSTATUS active\n\n'
    'TASK S1\n\tTITLE "Empty the cart in one click"\n\tSTATUS todo\n\tTYPE feat\n\tMILESTONE @MILESTONE.M1\n'
)
FORGELESS_BUILDER_PLAY = (
    READ_THE_BRIEF + AWAIT_THE_RELEASE + 'task=$(read_argument task | sed "s/^@TASK\\.//")\n'
    'printf \'%s\\n\' "$task" > "delivered-$task.txt"\n'
    "grep -rl 'STATUS todo' corpus | xargs sed -i 's/STATUS todo/STATUS implemented/'\n"
    'git add -- "delivered-$task.txt" corpus && git commit --quiet -m "feat: deliver $task" >&2\n'
    "brigade task check >&2\n"
    'cat -- "$1"\n'
)
FORGELESS_REVIEWER_PLAY = (
    READ_THE_BRIEF + AWAIT_THE_RELEASE + 'verdict="$BRIGADE_RUN_DIR/verdict.json"\n'
    'printf \'{"head": "%s", "verdict": "pass", "findings": []}\\n\' "$(git rev-parse HEAD)" > "$verdict"\n'
    'brigade verify verdict --file "$verdict" >&2\n'
    'cat -- "$1"\n'
)


class ForgelessWaveRehearser(WaveRehearser):
    def prepare_sandbox(self, path):
        super().prepare_sandbox(path)
        self.project.run_git("remote", "remove", "origin")

    def prepare_client(self, recordings, plays):
        super().prepare_client(recordings, plays)
        (plays / "planner").write_text((plays / "planner").read_text().replace(self._read_plan(plays), ONE_TASK_PLAN))
        (plays / "builder").write_text(FORGELESS_BUILDER_PLAY)
        (plays / "reviewer").write_text(FORGELESS_REVIEWER_PLAY)

    @staticmethod
    def _read_plan(plays) -> str:
        return (plays / "planner").read_text().split("<<'PLAN'\n", 1)[1].split("PLAN\n", 1)[0]

    def register_sandbox(self):
        self.run_brigade("project", "add", str(self.project.path), "--acceptance", "true")

    def is_milestone_reported(self) -> bool:
        events = self.read_events()
        merged = [event for event in events if event["event"] == "task.state" and event["state"] == "merged"]
        reported = [event for event in events if event["event"] == "milestone.reported"]
        return len(merged) == 1 and bool(reported)


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
        names = [event["event"] for event in self.rehearser.read_events()]

        # Assert
        for name in ("task.preflighted", "task.verdict", "pr.merged", "wave.closed"):
            with self.subTest(event=name):
                self.assertIn(name, names)

    def test_should_record_the_merge_of_the_task_with_no_pull_request(self):
        # Act
        [merged] = [event for event in self.rehearser.read_events() if event["event"] == "pr.merged"]

        # Assert
        self.assertNotIn("pr", merged)

    def test_should_merge_the_task_into_the_branch_of_its_milestone(self):
        # Assert
        self.assertEqual(self.delivered_on_the_branch, "S1\n")

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
        # Assert
        self.assertIn(f"to merge: {self.merge_command}\n", self.tick_before_the_merge.stdout)

    def test_should_close_the_milestone_with_no_pull_request_once_the_user_merged_its_branch(self):
        # Act
        [closed] = [event for event in self.rehearser.read_events() if event["event"] == "milestone.closed"]

        # Assert
        self.assertEqual(
            closed,
            {"schema_version": 1, "ts": ANY, "event": "milestone.closed", "project": "shop", "milestone": "M1"},
        )
