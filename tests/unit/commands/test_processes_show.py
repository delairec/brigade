import argparse
import tempfile
import unittest
from pathlib import Path

from brigade.commands.processes_show import COMMAND, processes_show
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

EXITED = '{"argv": ["git", "status"], "outcome": "exited", "exit": 0, "duration_ms": 12}\n'
FAILED = '{"argv": ["git", "push"], "outcome": "exited", "exit": 1, "duration_ms": 30}\n'


class ProcessesShowTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.runtime = create_test_runtime(create_test_paths(Path(self.root.name)))
        commands = self.runtime.paths.state_root / "commands"
        commands.mkdir(parents=True)
        (commands / "20261019T090000Z-a1b2c3.jsonl").write_text(EXITED + FAILED)

    def test_should_keep_the_failed_processes_of_the_invocation_when_asked(self):
        # Arrange
        request = argparse.Namespace(id="20261019T090000Z-a1b2c3", failed=True)

        # Act
        document = processes_show(request, self.runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "kind": "command",
                "id": "20261019T090000Z-a1b2c3",
                "processes": [{"argv": ["git", "push"], "outcome": "exited", "exit": 1, "duration_ms": 30}],
            },
        )


class ProcessesShowRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_they_are(self):
        # Arrange
        options = argparse.Namespace(id="r1", failed=False)

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertEqual(request, argparse.Namespace(id="r1", failed=False))


class ProcessesShowExitCodeTest(unittest.TestCase):
    def test_should_exit_0_once_the_trail_is_read(self):
        # Arrange
        document = {"processes": []}

        # Act
        exit_code = COMMAND.decide_exit_code(document)

        # Assert
        self.assertEqual(exit_code, 0)


class ProcessesShowTextTest(unittest.TestCase):
    def test_should_print_the_exit_code_else_the_duration_else_a_dash(self):
        # Arrange
        document = {
            "processes": [
                {"argv": ["git", "commit", "-m", "a message"], "outcome": "exited", "exit": 1, "duration_ms": 30},
                {"argv": ["claude", "-p"], "outcome": "killed", "exit": None, "duration_ms": 5},
                {"argv": ["sleep", "10"], "outcome": "running", "exit": None, "duration_ms": None},
            ]
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "exited  1  git commit -m 'a message'\nkilled  5 ms  claude -p\nrunning  -  sleep 10",
        )

    def test_should_print_an_exit_code_of_0(self):
        # Arrange
        document = {"processes": [{"argv": ["git", "status"], "outcome": "exited", "exit": 0, "duration_ms": 12}]}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, "exited  0  git status")
