from unittest.mock import ANY

from tests.cli.temporary_machine import CLONE_ENTRY_POINT
from tests.cli.test_task import TASK_BRANCH
from tests.cli.test_task_pr import SUBJECT, TYPED_TASKS, TaskPrTestCase

PROMOTED_TASK = (
    'TASK S3\n\tTITLE "Empty the cart in one click"\n\tSTATUS implemented\n\tDELIVERED_BY {pr}\n\tTYPE feat\n'
    '\tCOMPONENT "cart button"\n\tMILESTONE @MILESTONE.M1\n'
    '\tSPEC "the button of src/cart/button.py, once pressed, empties the cart"\n'
    '\tSPEC "the emptying charges nothing"\n'
)
OTHER_TASK_PR_OPENED = (
    '{"schema_version": 1, "ts": "2026-10-17T12:00:00Z", "event": "task.pr_opened", "project": "shop",'
    ' "task": "S6", "wave": "M1", "branch": "task/M1-empty-cart/S6", "pr": 43, "login": "octo-bot"}\n'
)
SCHEMA_WITHOUT_DELIVERED_BY = (
    'SCHEMA TASK\n\tDESC "a change delivered by one pull request"\n\tFIELD TITLE string\n\t\tREQUIRED\n'
    "\tFIELD STATUS todo|implemented\n\t\tREQUIRED\n\tFIELD TYPE feat|fix\n\tFIELD COMPONENT string\n"
    "\tFIELD MILESTONE @MILESTONE\n\tFIELD SPEC string\n\t\tREPEATABLE\n\t\tFIELD IMPL anchor\n"
    '\t\t\tREPEATABLE\n\nSCHEMA MILESTONE\n\tDESC "the tasks planned for one request"\n'
    "\tFIELD TITLE string\n\t\tREQUIRED\n\tFIELD STATUS planned|running\n\t\tREQUIRED\n"
)
SCHEMA_WITHOUT_IMPLEMENTED = (
    'SCHEMA TASK\n\tDESC "a change delivered by one pull request"\n\tFIELD TITLE string\n\t\tREQUIRED\n'
    "\tFIELD STATUS todo|done\n\t\tREQUIRED\n\tFIELD TYPE feat|fix\n\tFIELD COMPONENT string\n"
    "\tFIELD MILESTONE @MILESTONE\n\tFIELD SPEC string\n\t\tREPEATABLE\n\t\tFIELD IMPL anchor\n"
    "\t\t\tREPEATABLE\n\tFIELD DELIVERED_BY uint\n\nSCHEMA MILESTONE\n"
    '\tDESC "the tasks planned for one request"\n\tFIELD TITLE string\n\t\tREQUIRED\n'
    "\tFIELD STATUS planned|running\n\t\tREQUIRED\n"
)

SCHEMA_WITHOUT_STATUS = (
    'SCHEMA TASK\n\tDESC "a change delivered by one pull request"\n\tFIELD TITLE string\n\t\tREQUIRED\n'
    "\tFIELD TYPE feat|fix\n\tFIELD COMPONENT string\n\tFIELD MILESTONE @MILESTONE\n\tFIELD SPEC string\n"
    "\t\tREPEATABLE\n\t\tFIELD IMPL anchor\n\t\t\tREPEATABLE\n\tFIELD DELIVERED_BY uint\n\nSCHEMA MILESTONE\n"
    '\tDESC "the tasks planned for one request"\n\tFIELD TITLE string\n\t\tREQUIRED\n'
    "\tFIELD STATUS planned|running\n\t\tREQUIRED\n"
)
TASKS_PROMOTED_BY_57 = (
    'TASK S2\n\tTITLE "Remove an item from the cart"\n\tSTATUS implemented\n\n'
    'TASK S3\n\tTITLE "Empty the cart in one click"\n\tSTATUS implemented\n\tDELIVERED_BY 57\n\tTYPE feat\n'
    '\tCOMPONENT "cart button"\n\tMILESTONE @MILESTONE.M1\n'
    '\tSPEC "the button of src/cart/button.py, once pressed, empties the cart"\n'
    '\tSPEC "the emptying charges nothing"\n\n'
    'TASK S6\n\tTITLE "Count the emptied carts"\n\tSTATUS todo\n\tMILESTONE @MILESTONE.M1\n'
)
TASKS_PROMOTED_BY_42 = (
    'TASK S2\n\tTITLE "Remove an item from the cart"\n\tSTATUS implemented\n\n'
    'TASK S3\n\tTITLE "Empty the cart in one click"\n\tSTATUS implemented\n\tDELIVERED_BY 42\n\tTYPE feat\n'
    '\tCOMPONENT "cart button"\n\tMILESTONE @MILESTONE.M1\n'
    '\tSPEC "the button of src/cart/button.py, once pressed, empties the cart"\n'
    '\tSPEC "the emptying charges nothing"\n\n'
    'TASK S6\n\tTITLE "Count the emptied carts"\n\tSTATUS todo\n\tMILESTONE @MILESTONE.M1\n'
)


class TaskPromoteTestCase(TaskPrTestCase):
    def run_task_promote(self, *arguments: str):
        return self.machine.run_brigade(
            CLONE_ENTRY_POINT,
            "task",
            "promote",
            *arguments,
            environment=self.describe_environment(),
            cwd=self.worktree,
        )

    def read_tasks(self) -> str:
        return (self.worktree / "corpus" / "tasks.awawa").read_text()

    def read_last_subject(self) -> str:
        return self.project.run_git("-C", str(self.worktree), "log", "-1", "--format=%s").strip()

    def write_schema(self, schema: str) -> None:
        (self.worktree / "corpus" / "_schema.awawa").write_text(schema)
        self.project.run_git("-C", str(self.worktree), "commit", "--quiet", "-am", "the schema")


class BrigadeTaskPromoteAfterItsPullRequestTest(TaskPromoteTestCase):
    def setUp(self):
        super().setUp()
        self.run_task_check()
        self.run_task_pr("--subject", SUBJECT)

    def test_should_set_the_task_implemented_and_delivered_by_its_pull_request(self):
        # Act
        completed = self.run_task_promote()

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stdout, f"@TASK.S3 implemented, delivered by #42, in {self.read_head()}\n", completed.stderr
        )
        self.assertIn(PROMOTED_TASK.format(pr=42), self.read_tasks())

    def test_should_commit_the_promotion_and_push_it(self):
        # Act
        self.run_task_promote()

        # Assert
        self.assertEqual(self.read_last_subject(), "docs(corpus): mark @TASK.S3 implemented, delivered by #42")
        self.assertEqual(
            self.project.run_git("-C", str(self.remote), "rev-parse", TASK_BRANCH).strip(), self.read_head()
        )

    def test_should_end_the_promotion_commit_on_the_attribution_lines(self):
        # Act
        self.run_task_promote()

        # Assert
        self.assertEqual(
            self.project.run_git("-C", str(self.worktree), "log", "-1", "--format=%B"),
            "docs(corpus): mark @TASK.S3 implemented, delivered by #42\n\nCo-Authored-By: Ada <ada@example.org>\n\n",
        )

    def test_should_push_the_promotion_as_the_login_of_the_build_slot(self):
        # Act
        self.run_task_promote()

        # Assert
        self.assertEqual(self.pushes.read_text(), "token-of-octo-bot\ntoken-of-octo-bot\n")

    def test_should_promote_on_the_pull_request_of_the_task_not_on_the_last_one_of_the_wave(self):
        # Arrange
        ledger = next((self.state / "ledger").glob("*.jsonl"))
        with ledger.open("a") as lines:
            lines.write(OTHER_TASK_PR_OPENED)

        # Act
        self.run_task_promote()

        # Assert
        self.assertIn(PROMOTED_TASK.format(pr=42), self.read_tasks())

    def test_should_promote_on_the_pull_request_the_option_names(self):
        # Act
        self.run_task_promote("--pr", "57")

        # Assert
        self.assertIn(PROMOTED_TASK.format(pr=57), self.read_tasks())


class BrigadeTaskPromoteOfAnAlreadyPromotedTaskTest(TaskPromoteTestCase):
    def setUp(self):
        super().setUp()
        self.run_task_promote("--pr", "57")
        self.promotion = self.read_head()

    def test_should_push_and_record_it_again_without_a_second_commit(self):
        # Act
        completed = self.run_task_promote("--pr", "57")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(self.read_head(), self.promotion, completed.stderr)
        self.assertEqual(self.read_tasks(), TASKS_PROMOTED_BY_57, completed.stderr)
        self.assertEqual(
            self.read_events("task.promoted")[-1],
            {
                "schema_version": 1,
                "ts": ANY,
                "event": "task.promoted",
                "project": "shop",
                "task": "S3",
                "pr": 57,
                "commit": self.promotion,
            },
        )

    def test_should_replace_the_pull_request_that_delivers_it(self):
        # Act
        completed = self.run_task_promote("--pr", "42")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(self.read_tasks(), TASKS_PROMOTED_BY_42, completed.stderr)


class BrigadeTaskPromoteRefusalTest(TaskPromoteTestCase):
    def assert_refused(self, completed, cause: str) -> None:
        self.assertEqual(completed.returncode, 1)
        self.assertIn(cause, completed.stderr)
        self.assertEqual(self.read_tasks(), TYPED_TASKS)
        self.assertEqual(self.read_events("task.promoted"), [])

    def test_should_refuse_a_task_whose_pull_request_is_neither_recorded_nor_named(self):
        # Act
        completed = self.run_task_promote()

        # Assert
        self.assert_refused(completed, "no pull request of @TASK.S3 is recorded in the ledger; name it with --pr")

    def test_should_refuse_a_schema_that_declares_no_delivered_by(self):
        # Arrange
        self.write_schema(SCHEMA_WITHOUT_DELIVERED_BY)

        # Act
        completed = self.run_task_promote("--pr", "42")

        # Assert
        self.assert_refused(completed, "the TASK schema of the corpus of shop declares no DELIVERED_BY")

    def test_should_refuse_a_schema_that_declares_no_status_implemented(self):
        # Arrange
        self.write_schema(SCHEMA_WITHOUT_IMPLEMENTED)

        # Act
        completed = self.run_task_promote("--pr", "42")

        # Assert
        self.assert_refused(completed, "the TASK schema of the corpus of shop declares no STATUS implemented")

    def test_should_refuse_a_schema_that_declares_no_status(self):
        # Arrange
        self.write_schema(SCHEMA_WITHOUT_STATUS)

        # Act
        completed = self.run_task_promote("--pr", "42")

        # Assert
        self.assert_refused(completed, "the TASK schema of the corpus of shop declares no STATUS implemented")
