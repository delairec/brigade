import json

from tests.cli.wave_tick_test_case import WAVE_BRANCH, LaunchingTickTestCase

TASK_BRANCH = "task/M1-empty-cart/S3"
FAILING_CHECK_RUN = {"__typename": "CheckRun", "name": "tests", "status": "COMPLETED", "conclusion": "FAILURE"}
S3_REBUILT_TWICE_THEN_PREFLIGHTED_ON_A_FAILING_CHECK = (
    '{{"schema_version": 2, "ts": "2026-10-13T09:00:00Z", "event": "wave.started", "wave": "shop_w1",'
    ' "project": "shop", "branch": "{wave_branch}", "tasks": ["S3"]}}\n'
    '{{"schema_version": 1, "ts": "2026-10-13T09:10:00Z", "event": "task.pr_opened", "project": "shop",'
    ' "task": "S3", "wave": "shop_w1", "branch": "{task_branch}", "pr": 12, "login": "octo-bot"}}\n'
    '{{"schema_version": 1, "ts": "2026-10-13T09:15:00Z", "event": "task.state", "wave": "shop_w1", "task": "S3",'
    ' "state": "pr_open"}}\n'
    '{{"schema_version": 1, "ts": "2026-10-13T09:25:00Z", "event": "task.state", "wave": "shop_w1", "task": "S3",'
    ' "state": "fixing", "reason": "the entity of the task amended on {wave_branch}"}}\n'
    '{{"schema_version": 2, "ts": "2026-10-13T09:39:00Z", "event": "run.finished", "wave": "shop_w1", "task": "S3",'
    ' "run": "20261013T092500Z-cd603c", "client": "fake", "project": "shop", "session": null,'
    ' "duration_ms": 1000, "usage": null, "exit": 12, "nulls": {{}},'
    ' "procedure": "awawa-task", "role": "builder", "slot": "build", "segment": 1, "outcome": "turn_limit",'
    ' "error_class": "turn_limit", "main_steps": 94, "total_steps": null}}\n'
    '{{"schema_version": 1, "ts": "2026-10-13T09:40:00Z", "event": "task.state", "wave": "shop_w1", "task": "S3",'
    ' "state": "fixing", "reason": "the entity of the task amended on {wave_branch}"}}\n'
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
        self.project.run_git("branch", TASK_BRANCH, WAVE_BRANCH)
        self.project.run_git("worktree", "add", "--quiet", str(self.worktree), TASK_BRANCH)
        head = self.project.run_git("rev-parse", TASK_BRANCH).strip()
        (self.pull_requests / "task-M1-empty-cart-S3.json").write_text(
            json.dumps(
                [
                    {
                        "number": 12,
                        "state": "OPEN",
                        "headRefOid": head,
                        "baseRefName": WAVE_BRANCH,
                        "reviewDecision": "",
                        "updatedAt": "2026-10-18T11:00:00Z",
                        "statusCheckRollup": [FAILING_CHECK_RUN],
                    }
                ]
            )
        )
        (self.state / "ledger" / "2026-10.jsonl").write_text(
            S3_REBUILT_TWICE_THEN_PREFLIGHTED_ON_A_FAILING_CHECK.format(
                wave_branch=WAVE_BRANCH, task_branch=TASK_BRANCH, head=head
            )
        )

    def test_should_plan_the_check_repair_of_the_failing_check_at_the_next_tick(self):
        # Act
        completed = self.run_tick("--dry-run", "--json")

        # Assert
        self.assertEqual(
            json.loads(completed.stdout)["plan"],
            [
                {
                    "project": "shop",
                    "wave": "shop_w1",
                    "branch": "integration/M1-empty-cart",
                    "task": "S3",
                    "pr": 12,
                    "worktree": str(self.worktree),
                    "checks": ["tests"],
                    "findings": [],
                }
            ],
            completed.stderr,
        )
