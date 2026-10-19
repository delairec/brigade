import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from brigade.commands.wave_show import COMMAND
from tests.unit.commands.command_runtime import create_corpus_double, create_runtime, write_operational_corpus

PLANNING_REQUEST = (
    ("PROJECT", "@PROJECT.tidepool"),
    ("TEXT", "add the tides"),
    ("STATUS", "planning"),
    ("CREATED_AT", "2026-09-30T21:00:00Z"),
)


class WaveShowTextTest(unittest.TestCase):
    def test_should_print_the_request_and_the_tasks_of_its_wave(self):
        # Arrange
        document = {
            "schema_version": 1,
            "request": "R1",
            "project": "tidepool",
            "text": "add the tides",
            "status": "running",
            "wave": "tidepool_w16",
            "milestone": "M4",
            "branch": "integration/M4-tides",
            "created_at": "2026-09-30T21:00:00Z",
            "waits_for": None,
            "tasks": [
                {
                    "task": "T7",
                    "state": "running",
                    "run": "20261001T090000Z-a1",
                    "pull_request": None,
                    "title": "tides",
                },
                {"task": "T8", "state": "queued", "run": None, "pull_request": 42, "title": "moons"},
            ],
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "@REQUEST.R1 of @PROJECT.tidepool  running\n"
            "add the tides\n"
            "wave        tidepool_w16\n"
            "milestone   M4\n"
            "branch      integration/M4-tides\n"
            "created at  2026-09-30T21:00:00Z\n"
            "waits for   -\n"
            "\n"
            "task  state    run                  pull request  title\n"
            "T7    running  20261001T090000Z-a1  -             tides\n"
            "T8    queued                        42            moons",
        )


class WaveShowExitCodeTest(unittest.TestCase):
    def test_should_succeed(self):
        # Act
        exit_code = COMMAND.decide_exit_code({"schema_version": 1})

        # Assert
        self.assertEqual(exit_code, 0)


class WaveShowRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_the_request(self):
        # Arrange
        options = SimpleNamespace(request="R1")

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)


class WaveShowOfARequestBeingPlannedTest(unittest.TestCase):
    def test_should_show_a_request_with_no_wave_yet(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(root)
        runtime = create_runtime(root, run_process=create_corpus_double({"REQUEST": {"R1": PLANNING_REQUEST}}))

        # Act
        document = COMMAND.run(SimpleNamespace(request="R1"), runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "request": "R1",
                "project": "tidepool",
                "text": "add the tides",
                "status": "planning",
                "wave": None,
                "milestone": None,
                "branch": None,
                "created_at": "2026-09-30T21:00:00Z",
                "waits_for": None,
                "tasks": [],
            },
        )
