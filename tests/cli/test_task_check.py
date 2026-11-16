import json
from unittest.mock import ANY

from tests.cli.temporary_machine import CLONE_ENTRY_POINT
from tests.cli.test_task import TaskContextTestCase

CHECKED_TASKS = (
    'TASK S2\n\tTITLE "Remove an item from the cart"\n\tSTATUS implemented\n\nTASK S3\n'
    '\tTITLE "Empty the cart in one click"\n\tSTATUS todo\n\tMILESTONE @MILESTONE.M1\n'
    '\tSPEC "the button of src/cart/button.py, once pressed, empties the cart"\n'
    '\tSPEC "the emptying charges nothing"\n\nTASK S6\n\tTITLE "Count the emptied carts"\n'
    "\tSTATUS todo\n\tMILESTONE @MILESTONE.M1\n"
)
PASSING_RECIPE = (
    'RECIPE acceptance\n\tSCHEMA_VERSION 1\n\tMAX_WALL 10\n\tSTEP command\n\t\tARGV "python3"\n\t\tARGV "--version"\n'
)


class TaskCheckTestCase(TaskContextTestCase):
    def setUp(self):
        super().setUp()
        (self.worktree / "corpus" / "tasks.awawa").write_text(CHECKED_TASKS)
        self.project.run_git("-C", str(self.worktree), "commit", "--quiet", "-am", "the checked tasks")

    def describe_project_recipes(self) -> str:
        return PASSING_RECIPE

    def run_task_check(self, *arguments: str, environment: dict | None = None):
        return self.machine.run_brigade(
            CLONE_ENTRY_POINT,
            "task",
            "check",
            *arguments,
            environment=environment or self.describe_environment(),
            cwd=self.worktree,
        )

    def read_head(self) -> str:
        return self.project.run_git("-C", str(self.worktree), "rev-parse", "HEAD").strip()


class BrigadeTaskCheckOfPassingCommandsTest(TaskCheckTestCase):
    def test_should_run_each_acceptance_step_then_the_checks_of_the_corpus_then_the_privacy_check(self):
        # Act
        completed = self.run_task_check("--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stderr, "")
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "project": "shop",
                "task": "S3",
                "head": self.read_head(),
                "checks": [
                    {
                        "command": "python3 --version",
                        "passed": True,
                        "duration_ms": ANY,
                        "tail": [],
                    },
                    {"command": "awawa fmt --check .", "passed": True, "duration_ms": ANY, "tail": []},
                    {"command": "awawa lint --strict .", "passed": True, "duration_ms": ANY, "tail": []},
                    {"command": "privacy", "passed": True, "duration_ms": ANY, "tail": []},
                ],
            },
        )
