from tests.cli.temporary_machine import CLONE_ENTRY_POINT
from tests.cli.test_task_pr import SUBJECT, TaskPrTestCase

PROMOTED_TASK = (
    'TASK S3\n\tTITLE "Empty the cart in one click"\n\tSTATUS implemented\n\tDELIVERED_BY 42\n\tTYPE feat\n'
    '\tCOMPONENT "cart button"\n\tMILESTONE @MILESTONE.M1\n'
    '\tSPEC "the button of src/cart/button.py, once pressed, empties the cart"\n'
    '\tSPEC "the emptying charges nothing"\n'
)


class BrigadeTaskPromoteAfterItsPullRequestTest(TaskPrTestCase):
    def setUp(self):
        super().setUp()
        self.run_task_check()
        self.run_task_pr("--subject", SUBJECT)

    def test_should_set_the_task_implemented_and_delivered_by_its_pull_request(self):
        # Act
        completed = self.machine.run_brigade(
            CLONE_ENTRY_POINT, "task", "promote", environment=self.describe_environment(), cwd=self.worktree
        )

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout, f"@TASK.S3 implemented, delivered by #42, in {self.read_head()}\n")
        self.assertEqual(completed.stderr, "")
        self.assertIn(PROMOTED_TASK, (self.worktree / "corpus" / "tasks.awawa").read_text())
