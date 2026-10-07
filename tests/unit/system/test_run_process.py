import unittest

from brigade.errors import ToolFailure, ToolNotFound
from brigade.system.run_process import ProcessRequest, run_process


class RunProcessTest(unittest.TestCase):
    def test_should_raise_tool_not_found_when_the_executable_is_absent(self):
        # Arrange
        request = ProcessRequest(argv=("nonexistent-command-xyz",), cwd="/", timeout_s=1.0)

        # Act
        with self.assertRaises(ToolNotFound) as raised:
            run_process(request)

        # Assert
        self.assertEqual(str(raised.exception), "nonexistent-command-xyz not on PATH")

    def test_should_raise_tool_failure_when_the_process_times_out(self):
        # Arrange
        request = ProcessRequest(argv=("sleep", "10"), cwd="/", timeout_s=0.01)

        # Act
        with self.assertRaises(ToolFailure) as raised:
            run_process(request)

        # Assert
        self.assertIn("timed out after", str(raised.exception))

    def test_should_raise_tool_failure_when_the_exit_code_is_not_acceptable(self):
        # Arrange
        request = ProcessRequest(argv=("false",), cwd="/", timeout_s=5.0)

        # Act
        with self.assertRaises(ToolFailure) as raised:
            run_process(request)

        # Assert
        self.assertIn("exited 1", str(raised.exception))

    def test_should_return_the_record_when_the_exit_code_is_acceptable(self):
        # Arrange
        request = ProcessRequest(argv=("echo", "hello"), cwd="/", timeout_s=5.0, acceptable_exit_codes=(0,))

        # Act
        record = run_process(request)

        # Assert
        self.assertEqual(record.exit_code, 0)
        self.assertEqual(record.stdout.strip(), "hello")

    def test_should_pass_the_stdin_to_the_process(self):
        # Arrange
        request = ProcessRequest(argv=("cat",), cwd="/", timeout_s=5.0, stdin="piped input")

        # Act
        record = run_process(request)

        # Assert
        self.assertEqual(record.stdout, "piped input")
