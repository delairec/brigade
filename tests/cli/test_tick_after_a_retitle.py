import json
from pathlib import Path

from tests.cli.wave_tick_test_case import (
    MILESTONE_BRANCH,
    MILESTONE_BRANCH_CUT,
    TASK_BRANCH,
    WAVE_TASKS,
    LaunchingTickTestCase,
)

S3_ALONE_IN_ITS_WAVE = (
    '{"schema_version": 2, "ts": "2026-10-13T09:00:00Z", "event": "wave.started", "wave": "shop_w1",'
    f' "project": "shop", "branch": "{MILESTONE_BRANCH}", "tasks": ["S3"]}}\n'
)
FIRST_TITLE = 'TITLE "Empty the cart in one click"'
AMENDED_TITLE = 'TITLE "Empty the whole cart with a single click"'


class TickAfterTheRetitleOfATaskWithAStandingBranchTest(LaunchingTickTestCase):
    def setUp(self):
        super().setUp()
        (self.state / "ledger" / "2026-10.jsonl").write_text(MILESTONE_BRANCH_CUT + S3_ALONE_IN_ITS_WAVE)
        self.run_tick("--once")
        self.wait_for_the_runs()
        self.amend_the_title_of_the_task_on_the_milestone_branch()

    def amend_the_title_of_the_task_on_the_milestone_branch(self) -> None:
        checkout = Path(self.root.name).resolve() / "amendment"
        self.project.run_git("worktree", "add", "--quiet", str(checkout), MILESTONE_BRANCH)
        (checkout / "corpus" / "tasks.awawa").write_text(WAVE_TASKS.replace(FIRST_TITLE, AMENDED_TITLE))
        self.project.run_git("-C", str(checkout), "commit", "--quiet", "-am", "retitle S3")
        self.project.run_git("worktree", "remove", str(checkout))

    def test_should_serve_the_task_on_the_branch_of_the_first_tick(self):
        # Act
        completed = self.run_tick("--dry-run", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        document = json.loads(completed.stdout)
        self.assertEqual(document["snapshot"]["waves"][0]["tasks"][0]["branch"], TASK_BRANCH)
