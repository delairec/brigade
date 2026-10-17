import json
from pathlib import Path
from unittest.mock import ANY

from tests.cli.temporary_machine import CLONE_ENTRY_POINT
from tests.cli.test_task import RUN_ID, TaskContextTestCase

CHECKED_TASKS = (
    'TASK S2\n\tTITLE "Remove an item from the cart"\n\tSTATUS implemented\n\nTASK S3\n'
    '\tTITLE "Empty the cart in one click"\n\tSTATUS todo\n\tMILESTONE @MILESTONE.M1\n'
    '\tSPEC "the button of src/cart/button.py, once pressed, empties the cart"\n'
    '\tSPEC "the emptying charges nothing"\n\nTASK S6\n\tTITLE "Count the emptied carts"\n'
    "\tSTATUS todo\n\tMILESTONE @MILESTONE.M1\n"
)
PASSING_LINE = "python3 -c \"print('the cart is empty')\""
FAILING_LINE = "python3 -c \"import sys; [print(f'line {n}') for n in range(1, 26)]; sys.exit(3)\""
UNSPLITTABLE_LINE = "python3 -c \"print('the cart is empty')"
LAST_TWENTY_LINES = (
    "line 6\nline 7\nline 8\nline 9\nline 10\nline 11\nline 12\nline 13\nline 14\nline 15\n"
    "line 16\nline 17\nline 18\nline 19\nline 20\nline 21\nline 22\nline 23\nline 24\nline 25\n"
)


class TaskCheckTestCase(TaskContextTestCase):
    def setUp(self):
        super().setUp()
        (self.worktree / "corpus" / "tasks.awawa").write_text(CHECKED_TASKS)

    def describe_project_commands(self) -> tuple[str, ...]:
        return ("--acceptance", PASSING_LINE)

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

    def locate_record(self) -> Path:
        return self.state / "checks" / "shop" / "S3.json"


class BrigadeTaskCheckOfPassingCommandsTest(TaskCheckTestCase):
    def test_should_run_each_acceptance_line_then_the_checks_of_the_corpus_in_their_order(self):
        # Act
        completed = self.run_task_check("--json")

        # Assert
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "project": "shop",
                "task": "S3",
                "head": self.read_head(),
                "checks": [
                    {"command": PASSING_LINE, "passed": True, "duration_ms": ANY, "tail": []},
                    {"command": "awawa fmt --check .", "passed": True, "duration_ms": ANY, "tail": []},
                    {"command": "awawa lint --strict .", "passed": True, "duration_ms": ANY, "tail": []},
                ],
            },
        )

    def test_should_print_one_line_per_command_its_verdict_the_command_and_its_duration(self):
        # Act
        completed = self.run_task_check()

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertRegex(
            completed.stdout,
            r"\Apass  python3 -c \"print\('the cart is empty'\)\"  \d+\.\d s\n"
            r"pass  awawa fmt --check \.  \d+\.\d s\n"
            r"pass  awawa lint --strict \.  \d+\.\d s\n\Z",
        )

    def test_should_record_the_verdicts_with_the_head_in_the_state_directory(self):
        # Arrange
        completed = self.run_task_check("--json")

        # Act
        record = json.loads(self.locate_record().read_text())

        # Assert
        self.assertEqual(record, json.loads(completed.stdout))


class BrigadeTaskCheckWithAFailingAcceptanceLineTest(TaskCheckTestCase):
    def describe_project_commands(self) -> tuple[str, ...]:
        return ("--acceptance", FAILING_LINE, "--acceptance", PASSING_LINE)

    def test_should_run_every_command_whatever_the_others_returned(self):
        # Act
        completed = self.run_task_check("--json")

        # Assert
        self.assertEqual(
            json.loads(completed.stdout)["checks"],
            [
                {"command": FAILING_LINE, "passed": False, "duration_ms": ANY, "tail": ANY},
                {"command": PASSING_LINE, "passed": True, "duration_ms": ANY, "tail": []},
                {"command": "awawa fmt --check .", "passed": True, "duration_ms": ANY, "tail": []},
                {"command": "awawa lint --strict .", "passed": True, "duration_ms": ANY, "tail": []},
            ],
        )

    def test_should_exit_1_and_print_the_last_twenty_lines_of_the_failing_command(self):
        # Act
        completed = self.run_task_check()

        # Assert
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertIn(f"\n$ {FAILING_LINE}\n{LAST_TWENTY_LINES}", completed.stdout)


class BrigadeTaskCheckWithALineShlexRefusesTest(TaskCheckTestCase):
    def describe_project_commands(self) -> tuple[str, ...]:
        return ("--acceptance", PASSING_LINE, "--acceptance", UNSPLITTABLE_LINE)

    def test_should_refuse_the_line_by_name_before_any_command_runs(self):
        # Act
        completed = self.run_task_check()

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertIn(f"the command {UNSPLITTABLE_LINE} cannot be split into an argv", completed.stderr)
        self.assertFalse(self.locate_record().exists())


class BrigadeTaskCheckInARunTest(TaskCheckTestCase):
    def test_should_write_the_whole_output_of_each_command_under_the_check_directory_of_the_run(self):
        # Arrange
        self.run_task_check(environment=self.describe_run_environment())

        # Act
        output = (self.state / "runs" / RUN_ID / "check" / "1.log").read_text()

        # Assert
        self.assertEqual(output, "the cart is empty\n")
