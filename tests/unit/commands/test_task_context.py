import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from brigade.commands.task_context import COMMAND
from brigade.errors import BrigadeError
from tests.unit.commands.command_runtime import create_machine_double, create_runtime

THE_TASK_OF_THE_BRANCH = None
MAIN_BRANCH_CHECKOUT = {
    ("git", "rev-parse", "--show-toplevel"): "/home/user/tidepool\n",
    ("git", "branch", "--show-current"): "main\n",
}
WORKTREE = {
    "ancestry": {"command": "git merge-base --is-ancestor origin/integration/M4 HEAD", "exit_code": 0},
    "setup": None,
}
TASK_COMMANDS = [
    {"command": "awawa context @TASK.T7", "exit_code": 0, "stderr": "", "output": "TASK T7\n"},
]
ACCEPTANCE = {"acceptance": ["python3 -m unittest"], "heavy": []}
RESERVED = {"task_number": 191, "temporary_directory": None, "attribution": []}


class TaskContextTextTest(unittest.TestCase):
    def test_should_print_the_sections_a_build_run_starts_from(self):
        # Arrange
        document = {
            "worktree": {**WORKTREE, "setup": "$ ln -s ../node_modules\nexit 0\n"},
            "task": TASK_COMMANDS,
            "rules": [{"command": "awawa context @RULE.kiss", "exit_code": 0, "stderr": "", "output": "RULE kiss\n"}],
            "project": "# AGENTS.md\n",
            "acceptance": {"acceptance": ["python3 -m unittest"], "heavy": ["python3 -m pytest tests/cli"]},
            "reserved": {
                "task_number": 191,
                "temporary_directory": "/home/user/.cache/brigade/T7",
                "attribution": ["Co-Authored-By: a model"],
            },
            "when_done": ["brigade task check", "brigade task pr"],
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "# worktree\n$ git merge-base --is-ancestor origin/integration/M4 HEAD\nexit 0\n"
            "$ ln -s ../node_modules\nexit 0\n\n"
            "# task\n$ awawa context @TASK.T7\nexit 0\nTASK T7\n\n"
            "# rules\n$ awawa context @RULE.kiss\nexit 0\nRULE kiss\n\n"
            "# project\n# AGENTS.md\n\n"
            "# acceptance\npython3 -m unittest\npython3 -m pytest tests/cli  (left to CI)\n\n"
            "# reserved\ntask number 191\nCo-Authored-By: a model\ntemporary directory /home/user/.cache/brigade/T7\n\n"
            "# when done\nbrigade task check\nbrigade task pr",
        )

    def test_should_leave_out_the_sections_a_project_does_not_provide(self):
        # Arrange
        document = {
            "worktree": WORKTREE,
            "task": TASK_COMMANDS,
            "rules": None,
            "project": None,
            "acceptance": ACCEPTANCE,
            "reserved": RESERVED,
            "when_done": ["brigade task pr"],
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "# worktree\n$ git merge-base --is-ancestor origin/integration/M4 HEAD\nexit 0\n\n"
            "# task\n$ awawa context @TASK.T7\nexit 0\nTASK T7\n\n"
            "# acceptance\npython3 -m unittest\n\n"
            "# reserved\ntask number 191\n\n"
            "# when done\nbrigade task pr",
        )


class TaskContextExitCodeTest(unittest.TestCase):
    def test_should_succeed(self):
        # Act
        exit_code = COMMAND.decide_exit_code({"schema_version": 1})

        # Assert
        self.assertEqual(exit_code, 0)


class TaskContextRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_the_request(self):
        # Arrange
        options = SimpleNamespace(task=None)

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)


class TaskContextOutsideATaskTest(unittest.TestCase):
    def test_should_refuse_a_branch_that_is_not_the_branch_of_a_task(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (root / "config").mkdir()
        (root / "config" / "config.toml").write_text("", encoding="utf-8")
        runtime = create_runtime(root, run_process=create_machine_double({}, MAIN_BRANCH_CHECKOUT))

        # Act
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(SimpleNamespace(task=THE_TASK_OF_THE_BRANCH), runtime)

        # Assert
        self.assertEqual(str(raised.exception), "the branch main is not a task/<slug>/<task> branch")
