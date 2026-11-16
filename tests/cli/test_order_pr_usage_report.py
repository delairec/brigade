import json
import sys
import unittest
from pathlib import Path

from tests.cli.list_finished_run_roles import list_finished_run_roles
from tests.cli.list_order_steps import list_order_steps
from tests.cli.wave_rehearser import READ_THE_BRIEF, ClassCleanupRegistrar, WaveRehearser

REVIEWED_BRANCH = "feature/S1-empty-the-cart"
REPORT_PATH = "docs/usage-reports/pull-requests/1.md"
REVIEWED_PULL_REQUEST = {
    "number": 1,
    "title": "feat: empty the cart",
    "body": "",
    "headRefName": REVIEWED_BRANCH,
    "baseRefName": "main",
    "state": "OPEN",
    "reviewDecision": "APPROVED",
    "reviews": 1,
    "author": "octo-build",
}
ORDER_REPORTER_PLAY = (
    READ_THE_BRIEF + 'run=$(read_argument run)\nanswer="$BRIGADE_RUN_DIR/report.awawa"\n'
    f'brigade order context "$run" --json | "{sys.executable}" -c '
    '\'import json, sys; print(json.load(sys.stdin)["answer"].rstrip())\' > "$answer"\n'
    'printf \'\\tNARRATIVE "verdict: the corpus carried the review"\\n\' >> "$answer"\n'
    'brigade order answer "$run" --file "$answer" >&2\n'
    'cat -- "$1"\n'
)


class BrigadeOrderOfTheRecipePrUsageReportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rehearser = WaveRehearser(ClassCleanupRegistrar(cls))
        (Path(cls.rehearser.root.name).resolve() / "plays" / "reporter").write_text(ORDER_REPORTER_PLAY)
        project = cls.rehearser.project
        project.run_git("switch", "--quiet", "--create", REVIEWED_BRANCH)
        project.write("cart.txt", "empty\n")
        project.track("cart.txt")
        project.run_git("commit", "--quiet", "-m", "feat: empty the cart")
        project.run_git("push", "--quiet", "origin", REVIEWED_BRANCH)
        project.run_git("switch", "--quiet", "main")
        (cls.rehearser.store / "pulls").mkdir()
        (cls.rehearser.store / "pulls" / "1.json").write_text(json.dumps(REVIEWED_PULL_REQUEST))
        cls.completed = cls.rehearser.run_brigade("order", "new", "pr-usage-report", "--project", "shop", "pr=1")

    def test_should_commit_the_report_on_the_branch_of_the_pull_request(self):
        # Act
        report = self.rehearser.read_remote_file(REVIEWED_BRANCH, REPORT_PATH)

        # Assert
        self.assertEqual(self.completed.returncode, 0, self.completed.stderr)
        self.assertIn("verdict: the corpus carried the review", report)

    def test_should_record_no_run_for_the_collectors_and_the_steps_of_the_run_of_the_judge_step(self):
        # Act
        events = self.rehearser.read_events()

        # Assert
        self.assertEqual(
            list_order_steps(events, "pr-usage-report"),
            [
                ("order.started", None),
                ("step.done", "1-collect"),
                ("step.done", "2-collect"),
                ("step.done", "3-collect"),
                ("step.done", "4-gate"),
                ("step.done", "5-judge"),
                ("step.done", "6-output"),
                ("order.done", None),
            ],
        )
        self.assertEqual(list_finished_run_roles(events), ["reporter"])
