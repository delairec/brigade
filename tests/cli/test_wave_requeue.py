import json
from unittest.mock import ANY

from tests.cli.temporary_machine import CLONE_ENTRY_POINT
from tests.cli.wave_tick_test_case import WAVE_BRANCH, LaunchingTickTestCase
from tests.value_matchers import DurationUnderMatcher, PatternMatcher

RUN_ID_PATTERN = r"^\d{8}T\d{6}Z-[0-9a-f]{6}$"

S3_PARKED_ON_A_DEAD_RUN = (
    '{"schema_version": 2, "ts": "2026-10-13T09:00:00Z", "event": "wave.started", "wave": "shop_w1",'
    f' "project": "shop", "branch": "{WAVE_BRANCH}", "tasks": ["S3"]}}\n'
    '{"schema_version": 1, "ts": "2026-10-13T10:00:00Z", "event": "task.parked", "wave": "shop_w1", "task": "S3",'
    ' "reason": "run dead: 20261013T093000Z-a00001", "blockers": []}\n'
)


class BrigadeWaveRequeueOfAParkedTaskTest(LaunchingTickTestCase):
    def setUp(self):
        super().setUp()
        (self.state / "ledger" / "2026-10.jsonl").write_text(S3_PARKED_ON_A_DEAD_RUN)

    def test_should_queue_the_parked_task_again_for_the_next_tick_to_launch_it(self):
        # Act
        requeued = self.requeue_then_tick()

        # Assert
        self.assertEqual(requeued.returncode, 0, requeued.stderr)
        self.assertEqual(requeued.stdout, "task S3 of shop_w1 queued\n", requeued.stderr)
        self.assertEqual(
            self.read_events(),
            [
                {
                    "schema_version": 2,
                    "ts": "2026-10-13T09:00:00Z",
                    "event": "wave.started",
                    "wave": "shop_w1",
                    "project": "shop",
                    "branch": "integration/M1-empty-cart",
                    "tasks": ["S3"],
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-13T10:00:00Z",
                    "event": "task.parked",
                    "wave": "shop_w1",
                    "task": "S3",
                    "reason": "run dead: 20261013T093000Z-a00001",
                    "blockers": [],
                },
                {
                    "schema_version": 1,
                    "ts": ANY,
                    "event": "task.state",
                    "wave": "shop_w1",
                    "task": "S3",
                    "state": "queued",
                    "reason": "brigade wave requeue",
                },
                {
                    "schema_version": 1,
                    "ts": ANY,
                    "event": "task.state",
                    "wave": "shop_w1",
                    "task": "S3",
                    "state": "running",
                },
                {
                    "schema_version": 2,
                    "ts": ANY,
                    "event": "run.finished",
                    "run": PatternMatcher(RUN_ID_PATTERN),
                    "segment": 1,
                    "procedure": "build-task",
                    "slot": "build",
                    "role": "builder",
                    "client": "fake",
                    "project": "shop",
                    "session": "fake-session",
                    "main_steps": 12,
                    "total_steps": None,
                    "duration_ms": DurationUnderMatcher(10000),
                    "usage": {
                        "input_tokens": 120,
                        "output_tokens": 3400,
                        "cache_creation_input_tokens": 16778,
                        "cache_read_input_tokens": 98000,
                    },
                    "outcome": "done",
                    "error_class": None,
                    "exit": 0,
                    "wave": "shop_w1",
                    "task": "S3",
                    "nulls": {"total_steps": "the client reads no transcript", "error_class": "the run did not fail"},
                    "cost_usd": 0.42,
                },
            ],
        )

    def requeue_then_tick(self):
        requeued = self.machine.run_brigade(
            CLONE_ENTRY_POINT, "wave", "requeue", "shop_w1", "S3", environment=self.describe_environment()
        )
        self.run_tick("--once")
        self.wait_for_the_runs()
        return requeued


S3_RULED_ON_MAIN = (
    'TASK S2\n\tTITLE "Remove an item from the cart"\n\tSTATUS implemented\n\n'
    'TASK S3\n\tTITLE "Empty the cart in two clicks"\n\tSTATUS todo\n'
)
S3_AS_PLANNED = (
    'TASK S2\n\tTITLE "Remove an item from the cart"\n\tSTATUS implemented\n\n'
    'TASK S3\n\tTITLE "Empty the cart in one click"\n\tSTATUS todo\n\tMILESTONE @MILESTONE.M1\n\tAFTER @TASK.S2\n'
)


class BrigadeWaveRequeueOfATaskWhoseWaveBranchMovedSinceItsCutTest(LaunchingTickTestCase):
    def setUp(self):
        super().setUp()
        (self.state / "ledger" / "2026-10.jsonl").write_text(S3_PARKED_ON_A_DEAD_RUN)
        self.project.run_git("branch", "task/M1-empty-cart/S3", WAVE_BRANCH)
        self.project.run_git("checkout", "--quiet", WAVE_BRANCH)
        self.project.write("docs/wave-report.md", "# shop_w1\n")
        self.project.track("docs")
        self.project.run_git("commit", "--quiet", "-m", "the report of shop_w1")
        self.project.run_git("checkout", "--quiet", "main")

    def test_should_launch_the_build_run_on_the_branch_put_back_on_the_wave_branch(self):
        # Act
        self.machine.run_brigade(
            CLONE_ENTRY_POINT, "wave", "requeue", "shop_w1", "S3", environment=self.describe_environment()
        )
        self.run_tick("--once")
        self.wait_for_the_runs()

        # Assert
        self.assertEqual(
            self.read_events()[-1],
            {
                "schema_version": 2,
                "ts": ANY,
                "event": "run.finished",
                "run": PatternMatcher(RUN_ID_PATTERN),
                "segment": 1,
                "procedure": "build-task",
                "slot": "build",
                "role": "builder",
                "client": "fake",
                "project": "shop",
                "session": "fake-session",
                "main_steps": 12,
                "total_steps": None,
                "duration_ms": ANY,
                "usage": ANY,
                "outcome": "done",
                "error_class": None,
                "exit": 0,
                "wave": "shop_w1",
                "task": "S3",
                "nulls": ANY,
                "cost_usd": 0.42,
            },
        )


class BrigadeWaveRequeueOfATaskRuledOnTheMainBranchTest(LaunchingTickTestCase):
    def setUp(self):
        super().setUp()
        (self.state / "ledger" / "2026-10.jsonl").write_text(S3_PARKED_ON_A_DEAD_RUN)

    def rule_on_main(self, tasks: str):
        self.project.write("corpus/tasks.awawa", tasks)
        self.project.track("corpus")
        self.project.run_git("commit", "--quiet", "-m", "a ruling on S3")

    def test_should_refuse_the_task_naming_the_two_branches_and_the_cancellation_of_the_wave(self):
        # Arrange
        self.rule_on_main(S3_RULED_ON_MAIN)

        # Act
        requeued = self.machine.run_brigade(
            CLONE_ENTRY_POINT, "wave", "requeue", "shop_w1", "S3", environment=self.describe_environment()
        )

        # Assert
        self.assertEqual(
            requeued.stderr,
            "brigade wave requeue: the task S3 of the wave shop_w1 differs between main and"
            " integration/M1-empty-cart: the ruling on main reaches it through brigade wave cancel shop_w1"
            " and a new wave cut from main\n",
        )
        self.assertEqual(requeued.returncode, 1)

    def test_should_leave_the_task_parked(self):
        # Arrange
        self.rule_on_main(S3_RULED_ON_MAIN)

        # Act
        self.machine.run_brigade(
            CLONE_ENTRY_POINT, "wave", "requeue", "shop_w1", "S3", environment=self.describe_environment()
        )

        # Assert
        self.assertEqual(
            self.read_events()[-1],
            {
                "schema_version": 1,
                "ts": "2026-10-13T10:00:00Z",
                "event": "task.parked",
                "wave": "shop_w1",
                "task": "S3",
                "reason": "run dead: 20261013T093000Z-a00001",
                "blockers": [],
            },
        )

    def test_should_queue_a_task_whose_entity_on_main_is_the_one_of_the_wave_branch(self):
        # Arrange
        self.rule_on_main(S3_AS_PLANNED)

        # Act
        requeued = self.machine.run_brigade(
            CLONE_ENTRY_POINT, "wave", "requeue", "shop_w1", "S3", environment=self.describe_environment()
        )

        # Assert
        self.assertEqual(requeued.stdout, "task S3 of shop_w1 queued\n", requeued.stderr)


TASK_BRANCH = "task/M1-empty-cart/S3"
SUCCESSFUL_CHECK_RUN = {"__typename": "CheckRun", "name": "tests", "status": "COMPLETED", "conclusion": "SUCCESS"}
S3_PARKED_AFTER_ITS_FIRST_VERDICT = (
    '{{"schema_version": 2, "ts": "2026-10-13T09:00:00Z", "event": "wave.started", "wave": "shop_w1",'
    ' "project": "shop", "branch": "{wave_branch}", "tasks": ["S3"]}}\n'
    '{{"schema_version": 1, "ts": "2026-10-13T09:10:00Z", "event": "task.pr_opened", "project": "shop",'
    ' "task": "S3", "wave": "shop_w1", "branch": "{task_branch}", "pr": 12, "login": "octo-bot"}}\n'
    '{{"schema_version": 1, "ts": "2026-10-13T09:15:00Z", "event": "task.state", "wave": "shop_w1", "task": "S3",'
    ' "state": "pr_open"}}\n'
    '{{"schema_version": 1, "ts": "2026-10-13T09:20:00Z", "event": "task.preflighted", "project": "shop",'
    ' "wave": "shop_w1", "task": "S3", "pr": 12, "head": "{head}", "checks": []}}\n'
    '{{"schema_version": 1, "ts": "2026-10-13T09:20:00Z", "event": "task.state", "wave": "shop_w1", "task": "S3",'
    ' "state": "verifying"}}\n'
    '{{"schema_version": 1, "ts": "2026-10-13T09:40:00Z", "event": "task.verdict", "project": "shop",'
    ' "wave": "shop_w1", "task": "S3", "pr": 12, "head": "{head}", "verdict": "changes",'
    ' "findings": [{{"severity": "major", "summary": "the cart is not emptied"}}], "login": null}}\n'
    '{{"schema_version": 1, "ts": "2026-10-13T09:45:00Z", "event": "task.parked", "wave": "shop_w1", "task": "S3",'
    ' "reason": "past 2 repair rounds", "blockers": []}}\n'
)


class BrigadeWaveRequeueOfATaskParkedAfterItsFirstVerdictTest(LaunchingTickTestCase):
    def setUp(self):
        super().setUp()
        self.project.run_git("branch", TASK_BRANCH, WAVE_BRANCH)
        remote = self.project.path.parent / "shop.git"
        self.project.run_git("init", "--quiet", "--bare", str(remote))
        self.project.run_git("remote", "add", "origin", str(remote))
        self.project.run_git("push", "--quiet", "origin", WAVE_BRANCH, TASK_BRANCH)
        self.head = self.project.run_git("rev-parse", TASK_BRANCH).strip()
        (self.pull_requests / "task-M1-empty-cart-S3.json").write_text(
            json.dumps(
                [
                    {
                        "number": 12,
                        "state": "OPEN",
                        "headRefOid": self.head,
                        "baseRefName": WAVE_BRANCH,
                        "reviewDecision": "",
                        "updatedAt": "2026-10-18T11:00:00Z",
                        "statusCheckRollup": [SUCCESSFUL_CHECK_RUN],
                        "commits": [],
                    }
                ]
            )
        )
        (self.pull_requests / "12.json").write_text(
            json.dumps(
                {
                    "number": 12,
                    "title": "feat(cart): empty the cart in one click (@TASK.S3)",
                    "body": "Empty the cart in one click",
                    "headRefName": TASK_BRANCH,
                    "headRefOid": self.head,
                    "statusCheckRollup": [SUCCESSFUL_CHECK_RUN],
                    "commits": [],
                }
            )
        )
        (self.state / "ledger" / "2026-10.jsonl").write_text(
            S3_PARKED_AFTER_ITS_FIRST_VERDICT.format(wave_branch=WAVE_BRANCH, task_branch=TASK_BRANCH, head=self.head)
        )

    def test_should_send_the_task_back_to_its_preflight_and_the_next_tick_preflights_its_head(self):
        # Act
        requeued = self.machine.run_brigade(
            CLONE_ENTRY_POINT, "wave", "requeue", "shop_w1", "S3", environment=self.describe_environment()
        )
        self.run_tick("--once")
        self.wait_for_the_runs()

        # Assert
        self.assertEqual(requeued.stdout, "task S3 of shop_w1 pr_open\n", requeued.stderr)
        self.assertEqual(
            self.read_events()[7:9],
            [
                {
                    "schema_version": 1,
                    "ts": ANY,
                    "event": "task.state",
                    "wave": "shop_w1",
                    "task": "S3",
                    "state": "pr_open",
                    "reason": "brigade wave requeue",
                },
                {
                    "schema_version": 1,
                    "ts": ANY,
                    "event": "task.preflighted",
                    "project": "shop",
                    "wave": "shop_w1",
                    "task": "S3",
                    "pr": 12,
                    "head": self.head,
                    "checks": ANY,
                },
            ],
        )

    def test_should_launch_no_build_run(self):
        # Act
        self.machine.run_brigade(
            CLONE_ENTRY_POINT, "wave", "requeue", "shop_w1", "S3", environment=self.describe_environment()
        )
        self.run_tick("--once")
        self.wait_for_the_runs()

        # Assert
        self.assertEqual(self.read_run_records(), [])
