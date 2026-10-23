import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.commands.wave_show import COMMAND
from brigade.errors import BrigadeError
from tests.unit.commands.command_runtime import create_runtime, write_ledger
from tests.unit.commands.run_directories import create_run_result

WAVE_STARTED = {
    "schema_version": 2,
    "ts": "2026-09-30T22:00:00Z",
    "event": "wave.started",
    "wave": "tidepool_w16",
    "project": "tidepool",
    "branch": "integration/tidepool_w16",
    "tasks": ["T7", "T8"],
}
T7_RUNNING = {
    "schema_version": 1,
    "ts": "2026-10-01T09:00:00Z",
    "event": "task.state",
    "wave": "tidepool_w16",
    "task": "T7",
    "state": "running",
}
T7_PR_OPENED = {
    "schema_version": 1,
    "ts": "2026-10-01T21:00:00Z",
    "event": "task.pr_opened",
    "project": "tidepool",
    "task": "T7",
    "wave": "tidepool_w16",
    "branch": "task/tidepool_w16/T7",
    "pr": 42,
    "login": "tidepool-bot",
}
T7_RUN_FINISHED = {
    **create_run_result("20261001T090000Z-a1", "done", "2026-10-01T21:30:00Z"),
    "wave": "tidepool_w16",
    "task": "T7",
}
T7_PR_OPEN = {**T7_RUNNING, "ts": "2026-10-01T22:00:00Z", "state": "pr_open"}
T8_QUEUED = {**T7_RUNNING, "task": "T8", "state": "queued"}
T8_PARKED = {
    "schema_version": 1,
    "ts": "2026-10-01T10:00:00Z",
    "event": "task.parked",
    "wave": "tidepool_w16",
    "task": "T8",
    "reason": "blocked",
    "blockers": ["OPEN_QUESTION.Undecided"],
}

WAVE_PR_OPENED = {
    "schema_version": 1,
    "ts": "2026-10-02T09:00:00Z",
    "event": "wave.pr_opened",
    "wave": "tidepool_w16",
    "pr": 77,
    "login": "tidepool-cli",
}


class WaveShowTextTest(unittest.TestCase):
    def test_should_print_the_wave_and_one_row_per_task(self):
        # Arrange
        document = {
            "schema_version": 1,
            "wave": "tidepool_w16",
            "project": "tidepool",
            "branch": "integration/tidepool_w16",
            "started_at": "2026-09-30T22:00:00Z",
            "last_event": "wave.started",
            "pull_request": 77,
            "tasks": [
                {"task": "T7", "state": "pr_open", "pull_request": 42, "run": "20261001T090000Z-a1"},
                {"task": "T8", "state": None, "pull_request": None, "run": None},
            ],
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "wave tidepool_w16 of @PROJECT.tidepool on integration/tidepool_w16,"
            " started 2026-09-30T22:00:00Z, last event wave.started, pull request 77\n"
            "task  state    pull request  run\n"
            "T7    pr_open  42            20261001T090000Z-a1\n"
            "T8    -        -             -",
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
        options = Namespace(wave="tidepool_w16")

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)


class WaveShowOfTheLedgerTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def test_should_show_each_task_with_its_last_state_its_pull_request_and_its_run(self):
        # Arrange
        write_ledger(self.root, [WAVE_STARTED, T7_RUNNING, T7_PR_OPENED, T7_RUN_FINISHED, T7_PR_OPEN])

        # Act
        document = COMMAND.run(Namespace(wave="tidepool_w16"), create_runtime(self.root))

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "wave": "tidepool_w16",
                "project": "tidepool",
                "branch": "integration/tidepool_w16",
                "started_at": "2026-09-30T22:00:00Z",
                "last_event": "wave.started",
                "pull_request": None,
                "tasks": [
                    {"task": "T7", "state": "pr_open", "pull_request": 42, "run": "20261001T090000Z-a1"},
                    {"task": "T8", "state": None, "pull_request": None, "run": None},
                ],
            },
        )

    def test_should_show_the_integration_pull_request_the_tick_opened(self):
        # Arrange
        write_ledger(self.root, [WAVE_STARTED, T7_PR_OPEN, WAVE_PR_OPENED])

        # Act
        document = COMMAND.run(Namespace(wave="tidepool_w16"), create_runtime(self.root))

        # Assert
        self.assertEqual(document["pull_request"], 77)

    def test_should_show_a_task_its_blockers_parked_as_parked(self):
        # Arrange
        write_ledger(self.root, [WAVE_STARTED, T8_QUEUED, T8_PARKED])

        # Act
        document = COMMAND.run(Namespace(wave="tidepool_w16"), create_runtime(self.root))

        # Assert
        self.assertEqual(document["tasks"][1], {"task": "T8", "state": "parked", "pull_request": None, "run": None})

    def test_should_refuse_a_wave_no_wave_started_names(self):
        # Arrange
        write_ledger(self.root, [WAVE_STARTED])

        # Act
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(Namespace(wave="tidepool_w17"), create_runtime(self.root))

        # Assert
        self.assertEqual(str(raised.exception), "no wave.started names the wave tidepool_w17")
