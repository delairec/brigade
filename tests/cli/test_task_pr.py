import os
from pathlib import Path

from tests.cli.temporary_machine import CLONE_ENTRY_POINT
from tests.cli.test_collect import install_executable
from tests.cli.test_task import TASK_BRANCH, WAVE_BRANCH
from tests.cli.test_task_check import TaskCheckTestCase

TYPED_SCHEMA = (
    "SCHEMA TASK\n"
    '\tDESC "a change delivered by one pull request"\n'
    "\tFIELD TITLE string\n\t\tREQUIRED\n"
    "\tFIELD STATUS todo|implemented\n\t\tREQUIRED\n"
    "\tFIELD TYPE feat|fix\n"
    "\tFIELD COMPONENT string\n"
    "\tFIELD MILESTONE @MILESTONE\n"
    "\tFIELD SPEC string\n\t\tREPEATABLE\n\t\tFIELD IMPL anchor\n\t\t\tREPEATABLE\n"
    "\tFIELD DELIVERED_BY uint\n"
    "\n"
    "SCHEMA MILESTONE\n"
    '\tDESC "the tasks planned for one request"\n'
    "\tFIELD TITLE string\n\t\tREQUIRED\n"
    "\tFIELD STATUS planned|running\n\t\tREQUIRED\n"
)
TYPED_TASKS = (
    'TASK S2\n\tTITLE "Remove an item from the cart"\n\tSTATUS implemented\n\n'
    'TASK S3\n\tTITLE "Empty the cart in one click"\n\tSTATUS todo\n\tTYPE feat\n\tCOMPONENT "cart button"\n'
    "\tMILESTONE @MILESTONE.M1\n"
    '\tSPEC "the button of src/cart/button.py, once pressed, empties the cart"\n'
    '\tSPEC "the emptying charges nothing"\n\n'
    'TASK S6\n\tTITLE "Count the emptied carts"\n\tSTATUS todo\n\tMILESTONE @MILESTONE.M1\n'
)
FAKE_GH = (
    "#!/bin/sh\n"
    'printf \'%s\\n\' "$*" >> "{calls}"\n'
    'case "$1 $2" in\n'
    '  "auth token") echo token-of-octo-bot ;;\n'
    '  "auth status") echo \'{{"hosts": {{"github.com": [{{"login": "octo-bot", "active": true}}]}}}}\' ;;\n'
    '  "api --paginate") cat "{milestones}" ;;\n'
    "  \"api --method\") echo '{{}}' ;;\n"
    '  "pr create") cat >> "{calls}"; echo https://github.com/acme/shop/pull/42 ;;\n'
    "esac\n"
)
PR_KEYS = 'attribution = ["Co-Authored-By: Ada <ada@example.org>"]\n[forge_accounts]\nbuild = "octo-bot"\n'
SUBJECT = "empty the cart in one click"
PULL_REQUEST_CREATION = (
    f"pr create --base {WAVE_BRANCH} --head {TASK_BRANCH} --milestone Empty cart"
    f" --title feat(cart-button): {SUBJECT} (@TASK.S3) --body-file -\n"
)


class TaskPrTestCase(TaskCheckTestCase):
    def setUp(self):
        super().setUp()
        root = Path(self.root.name).resolve()
        self.gh_calls = root / "gh-calls"
        self.milestones = root / "milestones"
        self.milestones.write_text("Wave engine\n")
        install_executable(root / "tools" / "gh", FAKE_GH.format(calls=self.gh_calls, milestones=self.milestones))
        self.remote = root / "remotes" / "shop.git"
        self.project.run_git("init", "--quiet", "--bare", str(self.remote))
        self.project.run_git("remote", "add", "origin", str(self.remote))
        self.configure(keys=PR_KEYS)
        self.write_task(TYPED_TASKS)

    def describe_environment(self) -> dict:
        tools = Path(self.root.name).resolve() / "tools"
        return {**super().describe_environment(), "PATH": f"{tools}{os.pathsep}{self.machine.search_path}"}

    def write_task(self, tasks: str) -> None:
        (self.worktree / "corpus" / "_schema.awawa").write_text(TYPED_SCHEMA)
        (self.worktree / "corpus" / "tasks.awawa").write_text(tasks)
        self.project.run_git("-C", str(self.worktree), "add", "corpus")
        self.project.run_git("-C", str(self.worktree), "commit", "--quiet", "-m", "the task")

    def run_task_pr(self, *arguments: str):
        return self.machine.run_brigade(
            CLONE_ENTRY_POINT,
            "task",
            "pr",
            *arguments,
            environment=self.describe_environment(),
            cwd=self.worktree,
        )

    def read_gh_calls(self) -> str:
        if not self.gh_calls.exists():
            return ""
        return self.gh_calls.read_text()


class BrigadeTaskPrAfterAPassingCheckTest(TaskPrTestCase):
    def setUp(self):
        super().setUp()
        self.run_task_check()

    def test_should_open_the_pull_request_on_the_wave_branch_titled_from_the_task_and_the_subject(self):
        # Act
        completed = self.run_task_pr("--subject", SUBJECT)

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout, "https://github.com/acme/shop/pull/42\n")
        self.assertEqual(completed.stderr, "")
        self.assertIn(PULL_REQUEST_CREATION, self.read_gh_calls())
