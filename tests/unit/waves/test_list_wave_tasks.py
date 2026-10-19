import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.ledger.append_event import append_event
from brigade.ledger.task_state import TaskState
from brigade.system.read_configuration import Configuration
from brigade.waves.list_wave_tasks import list_wave_tasks
from tests.unit.create_scripted_runtime import create_scripted_runtime
from tests.unit.scripted_processes import ScriptedProcesses

REQUEST = {"project": "oak", "branch": "integration/F0-parser", "milestone": "F0", "wave": "oak_w1"}
REQUEST_NOT_PLANNED = {"project": "oak", "branch": None, "milestone": None, "wave": None}


class ListWaveTasksTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.processes = ScriptedProcesses()
        self.runtime = create_scripted_runtime(self.root, self.processes)

    def test_should_list_the_tasks_of_the_milestone_with_their_state_in_the_wave(self):
        # Arrange
        self.processes.answer_entities(
            self.runtime.paths.config_root, "PROJECT", {"oak": (("PATH", "/srv/oak"), ("CORPUS", "corpus"))}
        )
        self.processes.answer(
            ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", "integration/F0-parser^{commit}"),
            stdout="c0ffee\n",
        )
        tree = self.root / "cache" / "refs" / "oak" / "c0ffee"
        tree.mkdir(parents=True)
        self.processes.answer_entities(
            tree,
            "TASK",
            {"B12": (("TITLE", "the parser"), ("DELIVERED_BY", "41")), "B13": (("TITLE", "the printer"),)},
            ("MILESTONE==@MILESTONE.F0",),
        )
        append_event(
            self.runtime.paths,
            datetime(2026, 10, 19, 8, 0, tzinfo=UTC),
            TaskState(wave="oak_w1", task="B12", state="merged"),
        )
        append_event(
            self.runtime.paths,
            datetime(2026, 10, 19, 8, 0, tzinfo=UTC),
            TaskState(wave="oak_w0", task="B13", state="parked"),
        )

        # Act
        tasks = list_wave_tasks(self.runtime, Configuration(), REQUEST)

        # Assert
        self.assertEqual(
            tasks,
            [
                {"task": "B12", "title": "the parser", "state": "merged", "pull_request": 41},
                {"task": "B13", "title": "the printer", "state": "queued", "pull_request": None},
            ],
        )

    def test_should_list_no_task_for_a_request_not_planned_on_a_branch(self):
        # Act
        tasks = list_wave_tasks(self.runtime, Configuration(), REQUEST_NOT_PLANNED)

        # Assert
        self.assertEqual(tasks, [])

    def test_should_refuse_a_project_that_declares_no_corpus(self):
        # Arrange
        self.processes.answer_entities(self.runtime.paths.config_root, "PROJECT", {"oak": (("PATH", "/srv/oak"),)})

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            list_wave_tasks(self.runtime, Configuration(), REQUEST)

        # Assert
        self.assertEqual(str(refusal.exception), "@PROJECT.oak declares no corpus")
