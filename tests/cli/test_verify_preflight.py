import json
import os
from pathlib import Path

from tests.cli.temporary_machine import CLONE_ENTRY_POINT
from tests.cli.test_collect import install_executable
from tests.cli.test_task import TASK_BRANCH, WAVE_BRANCH, TaskContextTestCase
from tests.cli.test_task_pr import TYPED_SCHEMA

DELIVERED_TASKS = (
    'TASK S2\n\tTITLE "Remove an item from the cart"\n\tSTATUS implemented\n\n'
    'TASK S3\n\tTITLE "Empty the cart in one click"\n\tSTATUS implemented\n\tDELIVERED_BY 42\n\tTYPE feat\n'
    '\tCOMPONENT "cart button"\n\tMILESTONE @MILESTONE.M1\n'
    '\tSPEC "the button of src/cart/button.py, once pressed, empties the cart"\n'
    '\t\tIMPL "src/cart/button.py::def empty_cart"\n'
    '\tSPEC "the emptying charges nothing"\n\t\tIMPL "src/billing/charge.py::def charge"\n\n'
    'TASK S6\n\tTITLE "Count the emptied carts"\n\tSTATUS todo\n\tMILESTONE @MILESTONE.M1\n'
)
WAVE_TASKS = (
    'TASK S2\n\tTITLE "Remove an item from the cart"\n\tSTATUS implemented\n\n'
    'TASK S3\n\tTITLE "Empty the cart in one click"\n\tSTATUS todo\n\tTYPE feat\n'
    '\tCOMPONENT "cart button"\n\tMILESTONE @MILESTONE.M1\n'
    '\tSPEC "the button of src/cart/button.py, once pressed, empties the cart"\n'
    '\tSPEC "the emptying charges nothing"\n\n'
    'TASK S6\n\tTITLE "Count the emptied carts"\n\tSTATUS todo\n\tMILESTONE @MILESTONE.M1\n'
)
BUTTON_SOURCE = "def empty_cart(cart):\n    cart.clear()\n"
CHARGE_SOURCE = "def charge(cart):\n    return 0\n"
PULL_REQUEST_TITLE = "feat(cart-button): empty the cart in one click (@TASK.S3)"
PULL_REQUEST_BODY = (
    "Empty the cart in one click\n\n## Acceptance criteria\n\n"
    "- the button of src/cart/button.py, once pressed, empties the cart\n- the emptying charges nothing\n\n"
    "## Checks of 0123abc\n\n- pass `python3 -m unittest` 1.0 s\n"
)
SUCCESSFUL_CHECK_RUN = {"__typename": "CheckRun", "name": "tests", "status": "COMPLETED", "conclusion": "SUCCESS"}
FAKE_GH = (
    "#!/bin/sh\n"
    'printf \'%s\\n\' "$*" >> "{calls}"\n'
    'case "$1 $2" in\n'
    '  "auth token") echo token-of-octo-cli ;;\n'
    '  "pr view") cat "{pull_request}" ;;\n'
    "esac\n"
)
CLI_KEYS = '[forge_accounts]\ncli = "octo-cli"\n'
LEDGER_LINES = (
    '{"schema_version": 2, "ts": "2026-10-17T09:00:00Z", "event": "wave.started", "wave": "shop_w1",'
    f' "project": "shop", "branch": "{WAVE_BRANCH}", "tasks": ["S3"]}}\n'
    '{"schema_version": 1, "ts": "2026-10-17T12:00:00Z", "event": "task.pr_opened", "project": "shop",'
    f' "task": "S3", "wave": "shop_w1", "branch": "{TASK_BRANCH}", "pr": 42, "login": "octo-bot"}}\n'
)


class VerifyPreflightTestCase(TaskContextTestCase):
    def setUp(self):
        super().setUp()
        root = Path(self.root.name).resolve()
        self.gh_calls = root / "gh-calls"
        self.pull_request = root / "pull-request.json"
        install_executable(root / "tools" / "gh", FAKE_GH.format(calls=self.gh_calls, pull_request=self.pull_request))
        self.configure(keys=CLI_KEYS)
        self.commit_in_worktree({"corpus/_schema.awawa": TYPED_SCHEMA, "corpus/tasks.awawa": WAVE_TASKS}, "the plan")
        self.project.run_git("branch", "--force", WAVE_BRANCH, TASK_BRANCH)
        self.commit_in_worktree(
            {
                "corpus/tasks.awawa": DELIVERED_TASKS,
                "src/cart/button.py": BUTTON_SOURCE,
                "src/billing/charge.py": CHARGE_SOURCE,
            },
            "the delivery",
        )
        self.remote = root / "remotes" / "shop.git"
        self.project.run_git("init", "--quiet", "--bare", str(self.remote))
        self.project.run_git("remote", "add", "origin", str(self.remote))
        self.project.run_git("push", "--quiet", "origin", WAVE_BRANCH, TASK_BRANCH)
        ledger = self.state / "ledger" / "2026-10.jsonl"
        ledger.parent.mkdir(parents=True, exist_ok=True)
        ledger.write_text(LEDGER_LINES)
        self.describe_pull_request()

    def describe_environment(self) -> dict:
        tools = Path(self.root.name).resolve() / "tools"
        return {**super().describe_environment(), "PATH": f"{tools}{os.pathsep}{self.machine.search_path}"}

    def commit_in_worktree(self, files: dict, message: str) -> None:
        for relative_path, content in files.items():
            path = self.worktree / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        self.project.run_git("-C", str(self.worktree), "add", "--all")
        self.project.run_git("-C", str(self.worktree), "commit", "--quiet", "-m", message)

    def read_head(self) -> str:
        return self.project.run_git("-C", str(self.worktree), "rev-parse", "HEAD").strip()

    def describe_pull_request(
        self,
        title: str = PULL_REQUEST_TITLE,
        body: str = PULL_REQUEST_BODY,
        check_runs: tuple = (SUCCESSFUL_CHECK_RUN,),
    ) -> None:
        self.pull_request.write_text(
            json.dumps(
                {
                    "number": 42,
                    "title": title,
                    "body": body,
                    "headRefName": TASK_BRANCH,
                    "headRefOid": self.read_head(),
                    "statusCheckRollup": list(check_runs),
                }
            )
        )

    def run_preflight(self, *arguments: str):
        return self.machine.run_brigade(
            CLONE_ENTRY_POINT,
            "verify",
            "preflight",
            *arguments,
            environment=self.describe_environment(),
            cwd=self.project.path,
        )


class BrigadeVerifyPreflightOfASoundPullRequestTest(VerifyPreflightTestCase):
    def test_should_print_one_line_per_check_its_verdict_and_its_name(self):
        # Act
        completed = self.run_preflight("42")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stdout,
            f"preflight of #42, @TASK.S3 at {self.read_head()}\n"
            "pass  ancestry\npass  checks\npass  corpus\npass  promotion\npass  untouched_files\npass  privacy\n"
            "pass  body\ninfo  size\n  3 files\n  9 lines\n  3 packages: corpus, src/billing, src/cart\n  0 layers\n",
        )
