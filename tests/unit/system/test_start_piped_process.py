import os
import sys
import unittest

from brigade.errors import ToolNotFound
from brigade.system.start_piped_process import PipedProcessRequest, start_piped_process

INHERITED_ENVIRONMENT = os.environ
LONG_WAIT_S = 10.0
SHORT_WAIT_S = 0.1
ECHO = "import sys\nfor line in sys.stdin:\n    sys.stdout.write(line.upper())\n    sys.stdout.flush()\n"
SILENT = "import sys\nsys.stdin.read()\n"
FAILING = "import sys\nsys.stderr.write('awawa is not on the PATH\\n')\nsys.exit(1)\n"
QUIET_FAILURE = "import sys\nsys.exit(3)\n"
CLOSING_ITS_OUTPUT = "import os\nimport sys\nos.close(1)\nsys.stdin.read()\n"


def start_python(test_case: unittest.TestCase, program: str):
    process = start_piped_process(
        PipedProcessRequest(argv=(sys.executable, "-c", program), cwd="/"), INHERITED_ENVIRONMENT
    )
    test_case.addCleanup(process.stop)
    return process


class StartPipedProcessTest(unittest.TestCase):
    def test_should_answer_a_line_sent_on_its_standard_input_on_its_standard_output(self):
        # Arrange
        process = start_python(self, ECHO)

        # Act
        process.send('{"project": "app"}\n')

        # Assert
        self.assertEqual(process.receive(LONG_WAIT_S), '{"PROJECT": "APP"}')

    def test_should_receive_nothing_from_a_process_that_answers_nothing_within_the_wait(self):
        # Arrange
        process = start_python(self, SILENT)

        # Act
        line = process.receive(SHORT_WAIT_S)

        # Assert
        self.assertIsNone(line)
        self.assertTrue(process.is_running())

    def test_should_describe_the_failure_of_a_process_by_what_it_wrote_on_stderr(self):
        # Arrange
        process = start_python(self, FAILING)

        # Act
        line = process.receive(LONG_WAIT_S)

        # Assert
        self.assertIsNone(line)
        self.assertEqual(process.describe_failure(), "awawa is not on the PATH")

    def test_should_describe_the_failure_of_a_silent_process_by_its_exit_code(self):
        # Arrange
        process = start_python(self, QUIET_FAILURE)

        # Act
        process.receive(LONG_WAIT_S)

        # Assert
        self.assertEqual(process.describe_failure(), "exited with code 3")

    def test_should_stop_the_process(self):
        # Arrange
        process = start_python(self, SILENT)

        # Act
        process.stop()

        # Assert
        self.assertFalse(process.is_running())

    def test_should_close_its_standard_input_once_stopped(self):
        # Arrange
        process = start_python(self, SILENT)

        # Act
        process.stop()

        # Assert
        self.assertTrue(process.process.stdin.closed)

    def test_should_run_in_a_session_of_its_own_so_a_signal_to_the_terminal_reaches_brigade_serve_alone(self):
        # Arrange
        process = start_python(self, SILENT)

        # Act
        session = os.getsid(process.process.pid)

        # Assert
        self.assertEqual(session, process.process.pid)

    def test_should_take_a_broken_pipe_as_a_process_that_stopped(self):
        # Arrange
        process = start_python(self, QUIET_FAILURE)
        process.receive(LONG_WAIT_S)

        # Act
        process.send("x" * 1_000_000 + "\n")

        # Assert
        self.assertFalse(process.is_running())

    def test_should_take_a_process_whose_output_ended_as_a_process_that_stopped(self):
        # Arrange
        process = start_python(self, CLOSING_ITS_OUTPUT)
        process.receive(LONG_WAIT_S)

        # Act
        running = process.is_running()

        # Assert
        self.assertFalse(running)


class StartPipedProcessOfAMissingProgramTest(unittest.TestCase):
    def test_should_refuse_naming_the_program(self):
        # Arrange
        request = PipedProcessRequest(argv=("brigade-absent-program",), cwd="/")

        # Act
        with self.assertRaises(ToolNotFound) as raised:
            start_piped_process(request, INHERITED_ENVIRONMENT)

        # Assert
        self.assertIn("brigade-absent-program", str(raised.exception))
