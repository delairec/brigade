import json
import re
from pathlib import Path
from unittest.mock import ANY

from tests.cli.run_test_case import DONE_RESULT
from tests.cli.wave_tick_test_case import (
    MILESTONE_BRANCH,
    MILESTONE_BRANCH_CUT,
    TASK_BRANCH,
    LaunchingTickTestCase,
)
from tests.value_matchers import PatternMatcher

SHA256_DIGEST = PatternMatcher("^[0-9a-f]{64}$")
NO_EDIT_TOOL_NAMED = {
    "steps_to_first_edit": "the client names no edit tool",
    "tokens_to_first_edit": "the client names no edit tool",
}

SUCCESSFUL_CHECK_RUN = {"__typename": "CheckRun", "name": "tests", "status": "COMPLETED", "conclusion": "SUCCESS"}
FIVE_HOUR_LIMIT_RESULT = {
    **DONE_RESULT,
    "outcome": "failed",
    "steps": 7,
    "error_class": "rate_limit",
    "message": "You've hit your 5-hour limit",
}
RESET_PASSED = "2026-10-13T10:00:00Z"
RESUME_AT_PASSED = "2026-10-13T10:30:00Z"
S3_IN_CHANGES_REQUESTED = (
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
    '{{"schema_version": 1, "ts": "2026-10-13T09:45:00Z", "event": "task.state", "wave": "shop_w1", "task": "S3",'
    ' "state": "changes_requested"}}\n'
)


FINISHED_INSTANT = re.compile(r'"ts": "[^"]+", "event": "run.finished"')
RESUME_AT = re.compile(r'"resume_at": "[^"]+"')


class BrigadeTickOfARemediationCutByARateLimitTest(LaunchingTickTestCase):
    def setUp(self):
        super().setUp()
        recordings = Path(self.root.name) / "recordings"
        (recordings / "remediator.json").write_text(json.dumps(FIVE_HOUR_LIMIT_RESULT))
        (recordings / "remediator.resumed.json").write_text(json.dumps(DONE_RESULT))
        self.project.run_git("branch", TASK_BRANCH, MILESTONE_BRANCH)
        self.project.run_git("worktree", "add", "--quiet", str(self.worktree), TASK_BRANCH)
        self.register_on_github("main", MILESTONE_BRANCH, TASK_BRANCH)
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
                        "statusCheckRollup": [SUCCESSFUL_CHECK_RUN],
                    }
                ]
            )
        )
        (self.state / "ledger" / "2026-10.jsonl").write_text(
            MILESTONE_BRANCH_CUT
            + S3_IN_CHANGES_REQUESTED.format(wave_branch=MILESTONE_BRANCH, task_branch=TASK_BRANCH, head=head)
        )

    def cut_then_resume_after_the_reset(self) -> None:
        self.run_tick("--once")
        self.wait_for_the_runs()
        self.run_tick("--once")
        self.wait_for_the_runs()
        current_month = max((self.state / "ledger").glob("*.jsonl"))
        finished_before_the_reset = FINISHED_INSTANT.sub(
            f'"ts": "{RESET_PASSED}", "event": "run.finished"', current_month.read_text()
        )
        current_month.write_text(RESUME_AT.sub(f'"resume_at": "{RESUME_AT_PASSED}"', finished_before_the_reset))
        self.run_tick("--once")
        self.wait_for_the_runs()

    def test_should_resume_the_cut_remediation_with_the_task_back_in_fixing(self):
        # Act
        self.cut_then_resume_after_the_reset()

        # Assert
        self.assertEqual(
            self.read_events()[11:],
            [
                {
                    "schema_version": 1,
                    "ts": ANY,
                    "event": "task.state",
                    "wave": "shop_w1",
                    "task": "S3",
                    "state": "paused:quota",
                },
                {"schema_version": 1, "ts": ANY, "event": "wave.resumed", "wave": "shop_w1", "reason": "quota"},
                {
                    "schema_version": 1,
                    "ts": ANY,
                    "event": "task.state",
                    "wave": "shop_w1",
                    "task": "S3",
                    "state": "fixing",
                    "reason": "resumed after the quota reset",
                },
                {
                    "schema_version": 2,
                    "ts": ANY,
                    "event": "run.finished",
                    "run": ANY,
                    "segment": 2,
                    "procedure": "remediate-pr",
                    "slot": "remediate",
                    "role": "remediator",
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
                    "role_digest": SHA256_DIGEST,
                    "procedure_digest": SHA256_DIGEST,
                    "shipped_budget": 50,
                    "nulls": ANY,
                    "cost_usd": 0.42,
                },
            ],
        )

    def test_should_leave_the_repair_rounds_of_the_task_unchanged(self):
        # Arrange
        self.cut_then_resume_after_the_reset()

        # Act
        completed = self.run_tick("--dry-run", "--json")

        # Assert
        self.assertEqual(json.loads(completed.stdout)["snapshot"]["waves"][0]["tasks"][0]["repair_rounds"], 0)
