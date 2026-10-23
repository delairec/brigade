import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.commands.verify_preflight import COMMAND
from brigade.errors import BrigadeError
from tests.unit.commands.command_runtime import create_machine_double, write_ledger
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

TASK_WORKTREE = {
    ("git", "rev-parse", "--show-toplevel"): "/home/user/tidepool-T7\n",
    ("git", "rev-parse", "--path-format=absolute", "--git-common-dir"): "/home/user/tidepool/.git\n",
}
TIDEPOOL_PROJECT = (("PATH", "/home/user/tidepool"),)
WAVE_STARTED = {
    "schema_version": 2,
    "ts": "2026-09-30T22:00:00Z",
    "event": "wave.started",
    "wave": "tidepool_w16",
    "project": "tidepool",
    "branch": "integration/M4-tides",
    "tasks": ["T7"],
}
TASK_PR_OPENED = {
    "schema_version": 1,
    "ts": "2026-10-01T22:00:00Z",
    "event": "task.pr_opened",
    "project": "tidepool",
    "task": "T7",
    "wave": "tidepool_w16",
    "branch": "task/M4-tides/T7",
    "pr": 42,
    "login": "tidepool-bot",
}
PASSED_CHECK = {"verdict": "pass", "name": "ci", "findings": []}
FAILED_CHECK = {"verdict": "fail", "name": "scope", "findings": ["brigade/cli.py is outside the task"]}


class ForgeDeclineDouble:
    def __init__(self):
        self.questions = []

    def __getattr__(self, operation: str):
        def decline(request: dict, runtime) -> dict:
            self.questions.append((operation, request))
            raise BrigadeError(f"the forge double declines {operation}")

        return decline


class VerifyPreflightTextTest(unittest.TestCase):
    def test_should_print_each_check_with_its_findings(self):
        # Arrange
        document = {"pr": 42, "task": "T7", "head": "8885daa", "checks": [PASSED_CHECK, FAILED_CHECK]}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "preflight of #42, @TASK.T7 at 8885daa\npass  ci\nfail  scope\n  brigade/cli.py is outside the task",
        )


class VerifyPreflightExitCodeTest(unittest.TestCase):
    def test_should_fail_when_one_check_fails(self):
        # Arrange
        rows = [("every check passed", [PASSED_CHECK], 0), ("one check failed", [PASSED_CHECK, FAILED_CHECK], 1)]
        for case, checks, expected_exit_code in rows:
            with self.subTest(case=case):
                # Act
                exit_code = COMMAND.decide_exit_code({"checks": checks})

                # Assert
                self.assertEqual(exit_code, expected_exit_code)


class VerifyPreflightRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_the_request(self):
        # Arrange
        options = Namespace(pr=42)

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)


class VerifyPreflightOfAPullRequestTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        (self.root / "config").mkdir()
        (self.root / "config" / "config.toml").write_text("", encoding="utf-8")
        write_ledger(self.root, [WAVE_STARTED, TASK_PR_OPENED])
        self.forge = ForgeDeclineDouble()
        self.runtime = create_test_runtime(
            create_test_paths(self.root),
            run_process=create_machine_double({"PROJECT": {"tidepool": TIDEPOOL_PROJECT}}, TASK_WORKTREE),
            resolve_plugin=lambda kind, name, **places: self.forge,
        )

    def test_should_ask_the_forge_about_the_pull_request_of_the_task(self):
        # Act
        with self.assertRaises(BrigadeError):
            COMMAND.run(Namespace(pr=42), self.runtime)

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
            COMMAND.run(Namespace(pr=41), self.runtime)

        # Assert
        self.assertEqual(str(raised.exception), "no task.pr_opened of @PROJECT.tidepool names the pull request #41")
