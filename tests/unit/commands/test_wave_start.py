import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from brigade.commands.wave_start import COMMAND
from brigade.errors import BrigadeError
from tests.unit.commands.command_runtime import create_corpus_double, create_runtime, write_operational_corpus

PLANNING_REQUEST = (("PROJECT", "@PROJECT.tidepool"), ("STATUS", "planning"))


class WaveStartTextTest(unittest.TestCase):
    def test_should_name_the_wave_started_and_its_milestone(self):
        # Arrange
        document = {
            "schema_version": 1,
            "request": "R1",
            "status": "running",
            "wave": "tidepool_w16",
            "milestone": "M4",
            "project": "tidepool",
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, "@REQUEST.R1 running, wave tidepool_w16, @MILESTONE.M4 of @PROJECT.tidepool")


class WaveStartExitCodeTest(unittest.TestCase):
    def test_should_succeed(self):
        # Act
        exit_code = COMMAND.decide_exit_code({"schema_version": 1})

        # Assert
        self.assertEqual(exit_code, 0)


class WaveStartRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_the_request(self):
        # Arrange
        options = SimpleNamespace(request="R1")

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)


class WaveStartOfARequestTest(unittest.TestCase):
    def test_should_refuse_a_request_not_yet_planned(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(root)
        runtime = create_runtime(root, run_process=create_corpus_double({"REQUEST": {"R1": PLANNING_REQUEST}}))

        # Act
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(SimpleNamespace(request="R1"), runtime)

        # Assert
        self.assertEqual(str(raised.exception), "@REQUEST.R1 is planning, not planned")
