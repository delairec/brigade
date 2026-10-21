import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from brigade.commands.verify_context import COMMAND
from brigade.errors import BrigadeError
from tests.unit.commands.command_runtime import create_machine_double, create_runtime, write_ledger
from tests.unit.commands.test_verify_preflight import (
    TASK_PR_OPENED,
    TASK_WORKTREE,
    TIDEPOOL_PROJECT,
    WAVE_STARTED,
    ForgeDeclineDouble,
)

AWAWA_CONTEXT = {
    "command": "awawa context @TASK.T7 --with-schema .",
    "exit_code": 0,
    "stderr": "",
    "output": "TASK T7\n",
}
DIFF = {"command": "git diff 0000000 8885daa", "exit_code": 0, "stderr": "", "output": "+def tide():\n"}
RULES = [
    {
        "trigger": "python_file",
        "command": "awawa context @TRIGGER.python_file",
        "exit_code": 0,
        "stderr": "",
        "output": "RULE pure\n",
    }
]
FAILED_CHECK = {"verdict": "fail", "name": "scope", "findings": ["brigade/cli.py is outside the task"]}


def create_document(rules: list[dict] | None) -> dict:
    return {
        "pr": 42,
        "task": "T7",
        "head": "8885daa",
        "context": [AWAWA_CONTEXT],
        "diff": DIFF,
        "preflight": [FAILED_CHECK],
        "rules": rules,
        "grades": ["critical", "high", "medium", "low"],
    }


class VerifyContextTextTest(unittest.TestCase):
    def test_should_print_each_section_under_its_heading(self):
        # Arrange
        document = create_document(RULES)

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "# head\n8885daa\n\n"
            "# task\n$ awawa context @TASK.T7 --with-schema .\nexit 0\nTASK T7\n\n"
            "# diff\n$ git diff 0000000 8885daa\nexit 0\n+def tide():\n\n"
            "# preflight\nfail  scope\n  brigade/cli.py is outside the task\n\n"
            "# rules\n$ awawa context @TRIGGER.python_file\nexit 0\nRULE pure\n\n"
            "# grades\ncritical\nhigh\nmedium\nlow",
        )

    def test_should_leave_the_rules_out_without_an_instructions_corpus(self):
        # Arrange
        no_instructions_corpus = None

        # Act
        text = COMMAND.render_text(create_document(no_instructions_corpus))

        # Assert
        self.assertNotIn("# rules", text)


class VerifyContextExitCodeTest(unittest.TestCase):
    def test_should_exit_0_whatever_the_preflight_found(self):
        # Act
        exit_code = COMMAND.decide_exit_code(create_document(RULES))

        # Assert
        self.assertEqual(exit_code, 0)


class VerifyContextRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_the_request(self):
        # Arrange
        options = SimpleNamespace(pr=42)

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)


class VerifyContextOfAPullRequestTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        (self.root / "config").mkdir()
        (self.root / "config" / "config.toml").write_text("", encoding="utf-8")
        write_ledger(self.root, [WAVE_STARTED, TASK_PR_OPENED])
        self.forge = ForgeDeclineDouble()
        self.runtime = create_runtime(
            self.root,
            run_process=create_machine_double({"PROJECT": {"tidepool": TIDEPOOL_PROJECT}}, TASK_WORKTREE),
            resolve_plugin=lambda kind, name, **places: self.forge,
        )

    def test_should_ask_the_forge_about_the_pull_request_of_the_task(self):
        # Act
        with self.assertRaises(BrigadeError):
            COMMAND.run(SimpleNamespace(pr=42), self.runtime)

        # Assert
        self.assertEqual(
            self.forge.questions,
            [
                (
                    "read_pull_request",
                    {"schema_version": 1, "repository": "/home/user/tidepool", "number": 42, "environment": {}},
                )
            ],
        )

    def test_should_refuse_a_pull_request_no_task_opened(self):
        # Act
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(SimpleNamespace(pr=41), self.runtime)

        # Assert
        self.assertEqual(str(raised.exception), "no task.pr_opened of @PROJECT.tidepool names the pull request #41")
