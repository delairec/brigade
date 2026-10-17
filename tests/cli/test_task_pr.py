import json
import os
from pathlib import Path
from unittest.mock import ANY

from tests.cli.temporary_machine import CLONE_ENTRY_POINT
from tests.cli.test_collect import install_executable
from tests.cli.test_task import TASK_BRANCH, WAVE_BRANCH
from tests.cli.test_task_check import FAILING_LINE, TaskCheckTestCase

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
UNTYPED_TASKS = (
    'TASK S2\n\tTITLE "Remove an item from the cart"\n\tSTATUS implemented\n\nTASK S3\n'
    '\tTITLE "Empty the cart in one click"\n\tSTATUS todo\n\tCOMPONENT "cart button"\n'
    "\tMILESTONE @MILESTONE.M1\n"
    '\tSPEC "the button of src/cart/button.py, once pressed, empties the cart"\n'
    '\tSPEC "the emptying charges nothing"\n\nTASK S6\n\tTITLE "Count the emptied carts"\n'
    "\tSTATUS todo\n\tMILESTONE @MILESTONE.M1\n"
)
UNPLANNED_TASKS = (
    'TASK S2\n\tTITLE "Remove an item from the cart"\n\tSTATUS implemented\n\nTASK S3\n'
    '\tTITLE "Empty the cart in one click"\n\tSTATUS todo\n\tTYPE feat\n\tCOMPONENT "cart button"\n'
    '\tSPEC "the button of src/cart/button.py, once pressed, empties the cart"\n'
    '\tSPEC "the emptying charges nothing"\n\nTASK S6\n\tTITLE "Count the emptied carts"\n'
    "\tSTATUS todo\n\tMILESTONE @MILESTONE.M1\n"
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
RECEIVING_HOOK = '#!/bin/sh\nprintf "%s\\n" "$GH_TOKEN" >> "{pushes}"\n'
MILESTONE_CREATION = "api --method POST repos/{owner}/{repo}/milestones -f title=Empty cart\n"


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
        self.pushes = root / "pushes"
        install_executable(self.remote / "hooks" / "pre-receive", RECEIVING_HOOK.format(pushes=self.pushes))
        self.project.run_git("remote", "add", "origin", str(self.remote))
        self.configure(keys=PR_KEYS)
        self.write_task(TYPED_TASKS)

    def describe_environment(self) -> dict:
        tools = Path(self.root.name).resolve() / "tools"
        return {**super().describe_environment(), "PATH": f"{tools}{os.pathsep}{os.environ['PATH']}"}

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

    def read_events(self, name: str) -> list[dict]:
        lines = [
            json.loads(line)
            for month in sorted((self.state / "ledger").glob("*.jsonl"))
            for line in month.read_text().splitlines()
        ]
        return [line for line in lines if line["event"] == name]


class BrigadeTaskPrAfterAPassingCheckTest(TaskPrTestCase):
    def setUp(self):
        super().setUp()
        self.run_task_check()

    def test_should_push_the_task_branch(self):
        # Act
        self.run_task_pr("--subject", SUBJECT)

        # Assert
        self.assertEqual(
            self.project.run_git("-C", str(self.remote), "rev-parse", TASK_BRANCH).strip(), self.read_head()
        )

    def test_should_push_the_task_branch_as_the_login_of_the_build_slot(self):
        # Act
        self.run_task_pr("--subject", SUBJECT)

        # Assert
        self.assertEqual(self.pushes.read_text(), "token-of-octo-bot\n")

    def test_should_open_the_pull_request_on_the_wave_branch_titled_from_the_task_and_the_subject(self):
        # Act
        completed = self.run_task_pr("--subject", SUBJECT)

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stdout), (0, "https://github.com/acme/shop/pull/42\n"), completed.stderr
        )
        self.assertIn(PULL_REQUEST_CREATION, self.read_gh_calls())

    def test_should_fill_the_body_with_the_task_its_criteria_its_checks_and_the_attribution(self):
        # Act
        self.run_task_pr("--subject", SUBJECT)

        # Assert
        self.assertRegex(
            self.read_gh_calls(),
            r"Empty the cart in one click\n\n## Acceptance criteria\n\n"
            r"- the button of src/cart/button\.py, once pressed, empties the cart\n- the emptying charges nothing\n\n"
            rf"## Checks of {self.read_head()}\n\n"
            r"- pass `python3 -c \"print\('the cart is empty'\)\"` \d+\.\d s\n"
            r"- pass `awawa fmt --check \.` \d+\.\d s\n- pass `awawa lint --strict \.` \d+\.\d s\n\n"
            r"Co-Authored-By: Ada <ada@example.org>\n",
        )

    def test_should_record_the_opening_of_the_pull_request_in_the_ledger(self):
        # Act
        self.run_task_pr("--subject", SUBJECT)

        # Assert
        self.assertEqual(
            self.read_events("task.pr_opened"),
            [
                {
                    "schema_version": 1,
                    "ts": ANY,
                    "event": "task.pr_opened",
                    "project": "shop",
                    "task": "S3",
                    "wave": "M1",
                    "branch": TASK_BRANCH,
                    "pr": 42,
                    "login": "octo-bot",
                }
            ],
        )

    def test_should_create_the_milestone_the_repository_lacks_and_record_its_creation(self):
        # Act
        self.run_task_pr("--subject", SUBJECT)

        # Assert
        self.assertIn(MILESTONE_CREATION, self.read_gh_calls())
        self.assertEqual(
            self.read_events("milestone.created"),
            [
                {
                    "schema_version": 1,
                    "ts": ANY,
                    "event": "milestone.created",
                    "project": "shop",
                    "title": "Empty cart",
                    "login": "octo-bot",
                }
            ],
        )


class BrigadeTaskPrOnARepositoryHoldingTheMilestoneTest(TaskPrTestCase):
    def setUp(self):
        super().setUp()
        self.milestones.write_text("Wave engine\nEmpty cart\n")
        self.run_task_check()

    def test_should_open_the_pull_request_on_the_milestone_without_creating_it(self):
        # Act
        self.run_task_pr("--subject", SUBJECT)

        # Assert
        self.assertNotIn(MILESTONE_CREATION, self.read_gh_calls())
        self.assertEqual(self.read_events("milestone.created"), [])


class BrigadeTaskPrRefusalTest(TaskPrTestCase):
    def assert_refused(self, completed, cause: str) -> None:
        self.assertEqual(completed.returncode, 1)
        self.assertIn(cause, completed.stderr)
        self.assertNotIn("pr create", self.read_gh_calls())
        self.assertEqual(self.read_events("task.pr_opened"), [])

    def test_should_refuse_a_task_no_check_was_recorded_for(self):
        # Act
        completed = self.run_task_pr("--subject", SUBJECT)

        # Assert
        self.assert_refused(completed, "no check of @TASK.S3 is recorded; run brigade task check")

    def test_should_refuse_a_task_whose_last_check_is_not_of_head(self):
        # Arrange
        self.run_task_check()
        checked = self.read_head()
        (self.worktree / "README.md").write_text("the cart empties in one click\n")
        self.project.run_git("-C", str(self.worktree), "add", "README.md")
        self.project.run_git("-C", str(self.worktree), "commit", "--quiet", "-m", "describe the button")

        # Act
        completed = self.run_task_pr("--subject", SUBJECT)

        # Assert
        self.assert_refused(
            completed,
            f"the last check of @TASK.S3 is of {checked}, not of HEAD {self.read_head()}; run brigade task check",
        )

    def test_should_refuse_a_task_without_a_subject(self):
        # Arrange
        self.run_task_check()

        # Act
        completed = self.run_task_pr()

        # Assert
        self.assert_refused(
            completed, "brigade task pr needs --subject, the subject of the pull request in the imperative"
        )

    def test_should_refuse_a_task_that_carries_no_type(self):
        # Arrange
        self.write_task(UNTYPED_TASKS)
        self.run_task_check()

        # Act
        completed = self.run_task_pr("--subject", SUBJECT)

        # Assert
        self.assert_refused(completed, "@TASK.S3 carries no TYPE, which the title of its pull request opens on")

    def test_should_refuse_a_task_that_carries_no_milestone(self):
        # Arrange
        self.write_task(UNPLANNED_TASKS)
        self.run_task_check()

        # Act
        completed = self.run_task_pr("--subject", SUBJECT)

        # Assert
        self.assert_refused(
            completed, "@TASK.S3 carries no MILESTONE, whose TITLE names the milestone of its pull request"
        )


class BrigadeTaskPrAfterAFailingCheckTest(TaskPrTestCase):
    def describe_project_commands(self) -> tuple[str, ...]:
        return ("--acceptance", FAILING_LINE)

    def test_should_refuse_a_task_whose_last_check_has_a_failing_command(self):
        # Arrange
        self.run_task_check()

        # Act
        completed = self.run_task_pr("--subject", SUBJECT)

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertIn(f"the last check of @TASK.S3 failed on {FAILING_LINE}; run brigade task check", completed.stderr)
        self.assertNotIn("pr create", self.read_gh_calls())
