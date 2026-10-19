import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from brigade.commands.runs_stop import COMMAND
from brigade.errors import BrigadeError
from tests.unit.commands.command_runtime import create_runtime
from tests.unit.commands.run_directories import FIRST_RUN, create_run_record, create_run_result, write_run


class RunsStopTextTest(unittest.TestCase):
    def test_should_print_the_state_and_the_outcome_the_run_ended_on(self):
        # Arrange
        document = {"schema_version": 1, "run": {"run": FIRST_RUN, "state": "finished", "outcome": "stopped"}}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, f"run {FIRST_RUN} finished on stopped")


class RunsStopExitCodeTest(unittest.TestCase):
    def test_should_succeed(self):
        # Act
        exit_code = COMMAND.decide_exit_code({"schema_version": 1, "run": {}})

        # Assert
        self.assertEqual(exit_code, 0)


class RunsStopRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_the_request(self):
        # Arrange
        options = SimpleNamespace(run=FIRST_RUN)

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)


class RunsStopOfAFinishedRunTest(unittest.TestCase):
    def test_should_refuse_to_stop_a_run_already_finished(self):
        # Arrange
        directory = self.enterContext(tempfile.TemporaryDirectory())
        root = Path(directory)
        write_run(
            root / "state",
            create_run_record(FIRST_RUN, None, None),
            create_run_result(FIRST_RUN, "done", "2026-10-07T09:12:00Z"),
        )

        # Act
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(SimpleNamespace(run=FIRST_RUN), create_runtime(root))

        # Assert
        self.assertEqual(str(raised.exception), f"run {FIRST_RUN} has already finished on done")
