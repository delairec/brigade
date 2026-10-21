import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from brigade.ledger.append_event import append_event
from brigade.ledger.task_parked import TaskParked
from brigade.ledger.task_state import TaskState
from brigade.waves.read_task_states import read_task_states
from tests.unit.create_scripted_runtime import create_scripted_runtime
from tests.unit.scripted_processes import ScriptedProcesses

INSTANT = datetime(2026, 10, 19, 9, 0, tzinfo=UTC)


class ReadTaskStatesTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.paths = create_scripted_runtime(self.root, ScriptedProcesses()).paths

    def test_should_read_a_task_parked_by_its_blockers_as_parked(self):
        # Arrange
        append_event(self.paths, INSTANT, TaskState(wave="shop_w1", task="S3", state="queued"))
        append_event(
            self.paths,
            INSTANT,
            TaskParked(wave="shop_w1", task="S3", reason="blocked", blockers=("OPEN_QUESTION.Undecided",)),
        )

        # Act
        states = read_task_states(self.root / "state", "shop_w1")

        # Assert
        self.assertEqual(states, {"S3": "parked"})

    def test_should_read_a_task_queued_again_after_its_parking_as_queued(self):
        # Arrange
        append_event(
            self.paths,
            INSTANT,
            TaskParked(wave="shop_w1", task="S3", reason="blocked", blockers=("OPEN_QUESTION.Undecided",)),
        )
        append_event(self.paths, INSTANT, TaskState(wave="shop_w1", task="S3", state="queued"))

        # Act
        states = read_task_states(self.root / "state", "shop_w1")

        # Assert
        self.assertEqual(states, {"S3": "queued"})
