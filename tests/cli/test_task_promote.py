from unittest.mock import ANY

from tests.cli.temporary_machine import CLONE_ENTRY_POINT
from tests.cli.test_task import TASK_BRANCH
from tests.cli.test_task_pr import SUBJECT, TYPED_SCHEMA, TYPED_TASKS, TaskPrTestCase

PROMOTED_TASK = (
    'TASK S3\n\tTITLE "Empty the cart in one click"\n\tSTATUS implemented\n\tDELIVERED_BY {pr}\n\tTYPE feat\n'
    '\tCOMPONENT "cart button"\n\tMILESTONE @MILESTONE.M1\n'
    '\tSPEC "the button of src/cart/button.py, once pressed, empties the cart"\n'
    '\tSPEC "the emptying charges nothing"\n\t\tIMPL "src/billing/charge.py::def charge"\n'
)
SCHEMA_WITHOUT_DELIVERED_BY = TYPED_SCHEMA.replace("\tFIELD DELIVERED_BY uint\n", "")
SCHEMA_WITHOUT_IMPLEMENTED = TYPED_SCHEMA.replace("\tFIELD STATUS todo|implemented\n", "\tFIELD STATUS todo|done\n")


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
        self.assertIn(PROMOTED_TASK.format(pr=42), self.read_tasks())

    def test_should_commit_the_promotion_and_push_it(self):
        # Act
        self.run_task_promote()

        # Assert
        self.assertEqual(
            (
                self.read_last_subject(),
                self.project.run_git("-C", str(self.remote), "rev-parse", TASK_BRANCH).strip(),
            ),
            ("docs(corpus): mark @TASK.S3 implemented, delivered by #42", self.read_head()),
        )

    def test_should_record_the_promotion_in_the_ledger(self):
        # Act
        self.run_task_promote()

        # Assert
        self.assertEqual(
            self.read_events("task.promoted"),
            [
                {
                    "schema_version": 1,
                    "ts": ANY,
                    "event": "task.promoted",
                    "project": "shop",
                    "task": "S3",
                    "pr": 42,
                    "commit": self.read_head(),
                }
            ],
        )

    def test_should_promote_on_the_pull_request_the_option_names(self):
        # Act
        self.run_task_promote("--pr", "57")

        # Assert
        self.assertIn(PROMOTED_TASK.format(pr=57), self.read_tasks())


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
