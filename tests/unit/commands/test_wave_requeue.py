import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.commands.wave_requeue import COMMAND
from brigade.errors import BrigadeError
from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.task_state import TaskState
from tests.unit.commands.command_runtime import write_ledger
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

WAVE_STARTED = {
    "schema_version": 2,
    "ts": "2026-10-19T08:00:00Z",
    "event": "wave.started",
    "wave": "tidepool_w16",
    "project": "tidepool",
    "branch": "integration/tidepool_w16",
    "tasks": ["T7", "T8"],
}
PARKED_ON_A_DEAD_RUN = {
    "schema_version": 1,
    "ts": "2026-10-19T08:30:00Z",
    "event": "task.parked",
    "wave": "tidepool_w16",
    "task": "T7",
    "reason": "run dead: 20261019T080500Z-a1b2c3",
    "blockers": [],
}
PARKED_ON_A_FAILED_SETUP = {
    "schema_version": 1,
    "ts": "2026-10-19T08:30:00Z",
    "event": "task.state",
    "wave": "tidepool_w16",
    "task": "T7",
    "state": "parked",
    "reason": "setup failed",
}
RUNNING = {
    "schema_version": 1,
    "ts": "2026-10-19T08:30:00Z",
    "event": "task.state",
    "wave": "tidepool_w16",
    "task": "T7",
    "state": "running",
}


class WaveRequeueTextTest(unittest.TestCase):
    def test_should_name_the_task_queued_again(self):
        # Arrange
        document = {"schema_version": 1, "wave": "tidepool_w16", "task": "T7", "state": "queued"}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, "task T7 of tidepool_w16 queued")


class WaveRequeueExitCodeTest(unittest.TestCase):
    def test_should_succeed(self):
        # Act
        exit_code = COMMAND.decide_exit_code(
            {"schema_version": 1, "wave": "tidepool_w16", "task": "T7", "state": "queued"}
        )

        # Assert
        self.assertEqual(exit_code, 0)


class WaveRequeueRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_the_request(self):
        # Arrange
        options = Namespace(wave="tidepool_w16", task="T7")

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)


class WaveRequeueOfAParkedTaskTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.runtime = create_test_runtime(create_test_paths(self.root))

    def test_should_record_the_parked_task_queued(self):
        for case, parking in [
            ("parked by task.parked", PARKED_ON_A_DEAD_RUN),
            ("parked by task.state", PARKED_ON_A_FAILED_SETUP),
        ]:
            with self.subTest(case=case):
                # Arrange
                write_ledger(self.root, [WAVE_STARTED, parking])

                # Act
                COMMAND.run(Namespace(wave="tidepool_w16", task="T7"), self.runtime)

                # Assert
                self.assertEqual(
                    read_ledger(self.runtime.paths.state_root).entries[-1].event,
                    TaskState(wave="tidepool_w16", task="T7", state="queued"),
                )

    def test_should_describe_the_task_queued_again(self):
        # Arrange
        write_ledger(self.root, [WAVE_STARTED, PARKED_ON_A_DEAD_RUN])

        # Act
        document = COMMAND.run(Namespace(wave="tidepool_w16", task="T7"), self.runtime)

        # Assert
        self.assertEqual(document, {"schema_version": 1, "wave": "tidepool_w16", "task": "T7", "state": "queued"})


class WaveRequeueRefusalTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.runtime = create_test_runtime(create_test_paths(self.root))

    def test_should_refuse_a_task_that_is_not_parked_naming_its_state(self):
        for case, events, expected_refusal in [
            ("running", [WAVE_STARTED, RUNNING], "the task T7 of the wave tidepool_w16 is running, not parked"),
            ("with no state yet", [WAVE_STARTED], "the task T7 of the wave tidepool_w16 is queued, not parked"),
        ]:
            with self.subTest(case=case):
                # Arrange
                write_ledger(self.root, events)

                # Act
                with self.assertRaises(BrigadeError) as raised:
                    COMMAND.run(Namespace(wave="tidepool_w16", task="T7"), self.runtime)

                # Assert
                self.assertEqual(str(raised.exception), expected_refusal)

    def test_should_refuse_a_task_outside_the_wave_naming_the_wave(self):
        # Arrange
        write_ledger(self.root, [WAVE_STARTED, PARKED_ON_A_DEAD_RUN])

        # Act
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(Namespace(wave="tidepool_w16", task="T9"), self.runtime)

        # Assert
        self.assertEqual(str(raised.exception), "the task T9 is not a task of the wave tidepool_w16")

    def test_should_refuse_a_wave_no_wave_started_names(self):
        # Arrange
        write_ledger(self.root, [WAVE_STARTED, PARKED_ON_A_DEAD_RUN])

        # Act
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(Namespace(wave="tidepool_w99", task="T7"), self.runtime)

        # Assert
        self.assertEqual(str(raised.exception), "no wave.started names the wave tidepool_w99")
