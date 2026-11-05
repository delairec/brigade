import json
from unittest.mock import ANY

from tests.cli.wave_tick_test_case import MILESTONE_BRANCH, MILESTONE_BRANCH_CUT, TASK_BRANCH, LaunchingTickTestCase
from tests.value_matchers import PatternMatcher

SHA256_DIGEST = PatternMatcher("^[0-9a-f]{64}$")
CHECK_LINK = "https://ci.example.com/shop/checks/1"
FAILING_CHECK_RUN = {"__typename": "CheckRun", "name": "tests", "status": "COMPLETED", "conclusion": "FAILURE"}
S3_REBUILT_TWICE_THEN_PREFLIGHTED_ON_A_FAILING_CHECK = (
    '{{"schema_version": 2, "ts": "2026-10-13T09:00:00Z", "event": "wave.started", "wave": "shop_w1",'
    ' "project": "shop", "branch": "{base}", "tasks": ["S3"]}}\n'
    '{{"schema_version": 1, "ts": "2026-10-13T09:10:00Z", "event": "task.pr_opened", "project": "shop",'
    ' "task": "S3", "wave": "shop_w1", "branch": "{task_branch}", "pr": 12, "login": "octo-bot"}}\n'
    '{{"schema_version": 1, "ts": "2026-10-13T09:15:00Z", "event": "task.state", "wave": "shop_w1", "task": "S3",'
    ' "state": "pr_open"}}\n'
    '{{"schema_version": 1, "ts": "2026-10-13T09:25:00Z", "event": "task.state", "wave": "shop_w1", "task": "S3",'
    ' "state": "fixing", "reason": "the entity of the task amended on {base}"}}\n'
    '{{"schema_version": 2, "ts": "2026-10-13T09:39:00Z", "event": "run.finished", "wave": "shop_w1", "task": "S3",'
    ' "run": "20261013T092500Z-cd603c", "client": "fake", "project": "shop", "session": null,'
    ' "duration_ms": 1000, "usage": null, "exit": 12, "nulls": {{}},'
    ' "procedure": "awawa-task", "role": "builder", "slot": "build", "segment": 1, "outcome": "turn_limit",'
    ' "error_class": "turn_limit", "main_steps": 94, "total_steps": null}}\n'
    '{{"schema_version": 1, "ts": "2026-10-13T09:40:00Z", "event": "task.state", "wave": "shop_w1", "task": "S3",'
    ' "state": "fixing", "reason": "the entity of the task amended on {base}"}}\n'
    '{{"schema_version": 2, "ts": "2026-10-13T10:10:00Z", "event": "run.finished", "wave": "shop_w1", "task": "S3",'
    ' "run": "20261013T094000Z-b81a07", "client": "fake", "project": "shop", "session": null,'
    ' "duration_ms": 1000, "usage": null, "exit": 0, "nulls": {{}},'
    ' "procedure": "awawa-task", "role": "builder", "slot": "build", "segment": 1, "outcome": "done",'
    ' "error_class": null, "main_steps": 40, "total_steps": null}}\n'
    '{{"schema_version": 1, "ts": "2026-10-13T10:20:00Z", "event": "task.preflighted", "project": "shop",'
    ' "wave": "shop_w1", "task": "S3", "pr": 12, "head": "{head}",'
    ' "checks": [{{"name": "checks", "verdict": "fail", "findings": ["tests: failure"]}}]}}\n'
)


class BrigadeTickOfATaskRebuiltTwiceWhosePreflightFailsACheckTest(LaunchingTickTestCase):
    def setUp(self):
        super().setUp()
        self.project.run_git("branch", TASK_BRANCH, MILESTONE_BRANCH)
        self.project.run_git("worktree", "add", "--quiet", str(self.worktree), TASK_BRANCH)
        head = self.project.run_git("rev-parse", TASK_BRANCH).strip()
        (self.pull_requests / "feature-S3-empty-the-cart-in-one-click.json").write_text(
            json.dumps(
                [
                    {
                        "number": 12,
                        "state": "OPEN",
                        "headRefOid": head,
                        "baseRefName": MILESTONE_BRANCH,
                        "reviewDecision": "",
                        "updatedAt": "2026-10-18T11:00:00Z",
                        "statusCheckRollup": [FAILING_CHECK_RUN],
                    }
                ]
            )
        )
        (self.pull_requests / "12.checks.json").write_text(json.dumps([{"name": "tests", "link": CHECK_LINK}]))
        (self.state / "ledger" / "2026-10.jsonl").write_text(
            MILESTONE_BRANCH_CUT
            + S3_REBUILT_TWICE_THEN_PREFLIGHTED_ON_A_FAILING_CHECK.format(
                base=MILESTONE_BRANCH, task_branch=TASK_BRANCH, head=head
            )
        )

    def test_should_launch_the_check_repair_of_the_failing_check_at_the_next_tick(self):
        # Act
        self.run_tick("--once")
        self.wait_for_the_runs()

        # Assert
        self.assertEqual(
            self.read_events()[9:],
            [
                {
                    "schema_version": 1,
                    "ts": ANY,
                    "event": "task.state",
                    "wave": "shop_w1",
                    "task": "S3",
                    "state": "fixing",
                },
                {
                    "schema_version": 2,
                    "ts": ANY,
                    "event": "run.finished",
                    "run": ANY,
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
                    "role_digest": SHA256_DIGEST,
                    "procedure_digest": SHA256_DIGEST,
                    "shipped_budget": 75,
                },
            ],
        )
        self.assertEqual(self.read_run_records()[-1]["worktree"], str(self.worktree))
