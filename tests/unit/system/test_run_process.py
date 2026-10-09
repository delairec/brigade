import unittest
from unittest.mock import ANY

from brigade.errors import ToolFailure, ToolNotFound
from brigade.system.process_trace import ProcessTrace
from brigade.system.run_process import ProcessRecord, ProcessRequest, run_process


class RunProcessPastItsTimeoutTest(unittest.TestCase):
    def setUp(self):
        self.traces = []
        self.request = ProcessRequest(argv=("sleep", "30"), cwd="/", timeout_s=0.1)

    def test_should_refuse_naming_the_command_and_its_timeout(self):
        # Act
        with self.assertRaises(ToolFailure) as refusal:
            run_process(self.request, self.traces.append)

        # Assert
        self.assertEqual(str(refusal.exception), "sleep 30 timed out after 0.1 s")

    def test_should_trace_the_command_timed_out_with_no_exit_code(self):
        # Act
        with self.assertRaises(ToolFailure):
            run_process(self.request, self.traces.append)

        # Assert
        self.assertEqual(
            self.traces,
            [ProcessTrace(argv=("sleep", "30"), cwd="/", outcome="timed_out", exit_code=None, duration_ms=ANY)],
        )


class RunProcessWithTheVariablesOfItsCallerTest(unittest.TestCase):
    def test_should_add_them_over_the_whitelisted_environment(self):
        # Arrange
        request = ProcessRequest(
            argv=("sh", "-c", 'printf "%s" "$GH_TOKEN"'),
            cwd="/",
            timeout_s=10,
            environment={"GH_TOKEN": "token-of-octo-bot"},
        )

        # Act
        record = run_process(request, [].append)

        # Assert
        self.assertEqual(record.stdout, "token-of-octo-bot")


class RunProcessOfAnAcceptedExitCodeTest(unittest.TestCase):
    def setUp(self):
        self.traces = []
        self.request = ProcessRequest(argv=("true",), cwd="/", timeout_s=10)

    def test_should_answer_the_record_with_the_milliseconds_the_process_took(self):
        # Act
        record = run_process(self.request, self.traces.append)

        # Assert
        self.assertEqual(
            record, ProcessRecord(argv=("true",), cwd="/", exit_code=0, stdout="", stderr="", duration_ms=ANY)
        )
        self.assertIsInstance(record.duration_ms, int)

    def test_should_trace_the_command_exited_with_its_code_and_duration(self):
        # Act
        record = run_process(self.request, self.traces.append)

        # Assert
        self.assertEqual(
            self.traces,
            [ProcessTrace(argv=("true",), cwd="/", outcome="exited", exit_code=0, duration_ms=record.duration_ms)],
        )


class RunProcessOfARefusedExitCodeTest(unittest.TestCase):
    def test_should_trace_the_command_before_refusing_it(self):
        # Arrange
        traces = []
        request = ProcessRequest(argv=("false",), cwd="/", timeout_s=10)

        # Act
        with self.assertRaises(ToolFailure):
            run_process(request, traces.append)

        # Assert
        self.assertEqual(
            traces, [ProcessTrace(argv=("false",), cwd="/", outcome="exited", exit_code=1, duration_ms=ANY)]
        )


class RunProcessInAWorkingDirectoryThatDoesNotExistTest(unittest.TestCase):
    def test_should_refuse_naming_the_directory_rather_than_the_command(self):
        # Arrange
        traces = []
        request = ProcessRequest(argv=("true",), cwd="/brigade-absent-directory", timeout_s=10)

        # Act
        with self.assertRaises(ToolFailure) as refusal:
            run_process(request, traces.append)

        # Assert
        self.assertEqual(str(refusal.exception), "true: no working directory /brigade-absent-directory")

    def test_should_not_report_the_command_off_the_path(self):
        # Arrange
        traces = []
        request = ProcessRequest(argv=("true",), cwd="/brigade-absent-directory", timeout_s=10)

        # Act
        with self.assertRaises(ToolFailure) as refusal:
            run_process(request, traces.append)

        # Assert
        self.assertNotIsInstance(refusal.exception, ToolNotFound)

    def test_should_trace_the_missing_directory_rather_than_a_command_off_the_path(self):
        # Arrange
        traces = []
        request = ProcessRequest(argv=("true",), cwd="/brigade-absent-directory", timeout_s=10)

        # Act
        with self.assertRaises(ToolFailure):
            run_process(request, traces.append)

        # Assert
        self.assertEqual(
            traces,
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


class RunProcessOfACommandOffThePathTest(unittest.TestCase):
    def test_should_trace_the_command_not_found_before_refusing_it(self):
        # Arrange
        traces = []
        request = ProcessRequest(argv=("brigade-absent-tool",), cwd="/", timeout_s=10)

        # Act
        with self.assertRaises(ToolNotFound):
            run_process(request, traces.append)

        # Assert
        self.assertEqual(
            traces,
            [
                ProcessTrace(
                    argv=("brigade-absent-tool",), cwd="/", outcome="not_found", exit_code=None, duration_ms=ANY
                )
            ],
        )
