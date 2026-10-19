import tempfile
import unittest
from pathlib import Path
from unittest.mock import ANY

from brigade.errors import CannotWrite, ToolFailure, ToolNotFound
from brigade.system.process_trace import ProcessTrace
from brigade.system.spawn_process import SpawnRequest, spawn_process

PROCESS_WAIT_S = 10.0
LARGER_THAN_A_PIPE = "x" * 1_048_576
STILL_RUNNING = None


class SpawnProcessTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.stdout = Path(self.root.name) / "stdout.log"
        self.stderr = Path(self.root.name) / "stderr.log"
        self.traces = []

    def spawn(self, argv: tuple, stdin):
        process = spawn_process(
            SpawnRequest(
                argv=argv, cwd=self.root.name, environment={}, stdin=stdin, stdout=self.stdout, stderr=self.stderr
            ),
            self.traces.append,
        )
        self.addCleanup(process.wait)
        self.addCleanup(process.kill)
        return process


class SpawnProcessWithABriefTest(SpawnProcessTestCase):
    def test_should_hand_the_brief_to_the_process_on_its_standard_input(self):
        # Arrange
        process = self.spawn(("cat",), "Deliver the task B70.\n")

        # Act
        process.wait(timeout=PROCESS_WAIT_S)

        # Assert
        self.assertEqual(self.stdout.read_text(), "Deliver the task B70.\n")

    def test_should_hand_the_process_over_before_it_reads_its_brief(self):
        # Act
        process = self.spawn(("sleep", "30"), LARGER_THAN_A_PIPE)

        # Assert
        self.assertEqual(process.poll(), STILL_RUNNING)

    def test_should_hand_a_brief_larger_than_a_pipe_whole(self):
        # Arrange
        process = self.spawn(("cat",), LARGER_THAN_A_PIPE)

        # Act
        process.wait(timeout=PROCESS_WAIT_S)

        # Assert
        self.assertEqual(self.stdout.read_text(), LARGER_THAN_A_PIPE)


class SpawnProcessOfAMissingToolTest(SpawnProcessTestCase):
    def spawn_missing_tool(self):
        spawn_process(
            SpawnRequest(
                argv=("brigade-no-such-tool",),
                cwd=self.root.name,
                environment={},
                stdin=None,
                stdout=self.stdout,
                stderr=self.stderr,
            ),
            self.traces.append,
        )

    def test_should_refuse_naming_the_tool_not_on_path(self):
        # Act
        with self.assertRaises(ToolNotFound) as refusal:
            self.spawn_missing_tool()

        # Assert
        self.assertEqual(str(refusal.exception), "brigade-no-such-tool not on PATH")

    def test_should_trace_the_tool_not_found_before_refusing_it(self):
        # Act
        with self.assertRaises(ToolNotFound):
            self.spawn_missing_tool()

        # Assert
        self.assertEqual(
            self.traces,
            [
                ProcessTrace(
                    argv=("brigade-no-such-tool",),
                    cwd=self.root.name,
                    outcome="not_found",
                    exit_code=None,
                    duration_ms=ANY,
                )
            ],
        )

    def test_should_trace_nothing_for_a_tool_it_spawns(self):
        # Act
        self.spawn(("true",), None)

        # Assert
        self.assertEqual(self.traces, [])


class SpawnProcessInAWorkingDirectoryThatDoesNotExistTest(SpawnProcessTestCase):
    def spawn_in_missing_directory(self):
        spawn_process(
            SpawnRequest(
                argv=("true",),
                cwd="/brigade-absent-directory",
                environment={},
                stdin=None,
                stdout=self.stdout,
                stderr=self.stderr,
            ),
            self.traces.append,
        )

    def test_should_refuse_naming_the_directory_rather_than_the_command(self):
        # Act
        with self.assertRaises(ToolFailure) as refusal:
            self.spawn_in_missing_directory()

        # Assert
        self.assertEqual(str(refusal.exception), "true: no working directory /brigade-absent-directory")

    def test_should_not_report_the_command_off_the_path(self):
        # Act
        with self.assertRaises(ToolFailure) as refusal:
            self.spawn_in_missing_directory()

        # Assert
        self.assertNotIsInstance(refusal.exception, ToolNotFound)

    def test_should_trace_the_missing_directory_rather_than_a_command_off_the_path(self):
        # Act
        with self.assertRaises(ToolFailure):
            self.spawn_in_missing_directory()

        # Assert
        self.assertEqual(
            self.traces,
            [
                ProcessTrace(
                    argv=("true",),
                    cwd="/brigade-absent-directory",
                    outcome="no_working_directory",
                    exit_code=None,
                    duration_ms=ANY,
                )
            ],
        )


class SpawnProcessIntoAnUnwritableLogTest(SpawnProcessTestCase):
    def test_should_refuse_naming_the_log_it_cannot_open(self):
        # Arrange
        unwritable = Path(self.root.name) / "missing" / "stdout.log"

        # Act
        with self.assertRaises(CannotWrite) as refusal:
            spawn_process(
                SpawnRequest(
                    argv=("true",),
                    cwd=self.root.name,
                    environment={},
                    stdin=None,
                    stdout=unwritable,
                    stderr=self.stderr,
                ),
                self.traces.append,
            )

        # Assert
        self.assertEqual(str(refusal.exception), f"cannot write {unwritable}: No such file or directory")
