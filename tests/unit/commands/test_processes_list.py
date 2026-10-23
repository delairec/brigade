import argparse
import tempfile
import unittest
from pathlib import Path

from brigade.commands.processes_list import COMMAND, processes_list
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

EXITED = '{"argv": ["git", "status"], "outcome": "exited", "exit": 0, "duration_ms": 12}\n'
FAILED = '{"argv": ["git", "push"], "outcome": "exited", "exit": 1, "duration_ms": 30}\n'


class ProcessesListTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.runtime = create_test_runtime(create_test_paths(Path(self.root.name)))
        commands = self.runtime.paths.state_root / "commands"
        commands.mkdir(parents=True)
        (commands / "20261019T090000Z-a1b2c3.jsonl").write_text(EXITED + FAILED)

    def test_should_count_the_processes_of_each_invocation_and_the_failed_ones(self):
        # Arrange
        no_option = argparse.Namespace()

        # Act
        document = processes_list(no_option, self.runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "invocations": [
                    {
                        "kind": "command",
                        "id": "20261019T090000Z-a1b2c3",
                        "instant": "2026-10-19T09:00:00Z",
                        "processes": 2,
                        "failed": 1,
                    }
                ],
            },
        )


class ProcessesListRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_they_are(self):
        # Arrange
        options = argparse.Namespace(json=True)

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertEqual(request, argparse.Namespace(json=True))


class ProcessesListExitCodeTest(unittest.TestCase):
    def test_should_exit_0_once_the_trails_are_read(self):
        # Arrange
        document = {"invocations": []}

        # Act
        exit_code = COMMAND.decide_exit_code(document)

        # Assert
        self.assertEqual(exit_code, 0)


class ProcessesListTextTest(unittest.TestCase):
    def test_should_print_one_row_per_invocation(self):
        # Arrange
        document = {
            "invocations": [
                {
                    "kind": "command",
                    "id": "20261019T090000Z-a1b2c3",
                    "instant": "2026-10-19T09:00:00Z",
                    "processes": 2,
                    "failed": 1,
                }
            ]
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "kind     id                       instant               processes  failed\n"
            "command  20261019T090000Z-a1b2c3  2026-10-19T09:00:00Z  2          1",
        )
