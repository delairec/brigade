import json
import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.system.read_configuration import Configuration
from brigade.waves.start_wave import start_wave
from tests.unit.create_scripted_runtime import create_scripted_runtime
from tests.unit.scripted_processes import ScriptedProcesses

REQUEST_FIELDS = (
    ("PROJECT", "@PROJECT.oak"),
    ("STATUS", "planned"),
    ("MILESTONE", "F0"),
    ("BRANCH", "integration/F0-parser"),
    ("CREATED_AT", "2026-10-19T08:00:00Z"),
)


class StartWaveTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.processes = ScriptedProcesses()
        self.runtime = create_scripted_runtime(self.root, self.processes)
        self.config_root = self.runtime.paths.config_root

    def prepare_planned_request(self) -> None:
        self.processes.answer_entity(self.config_root, "REQUEST", "oak_1", REQUEST_FIELDS)
        self.processes.answer_entities(self.config_root, "PROJECT", {"oak": (("PATH", "/srv/oak"),)})
        self.processes.answer(
            ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", "integration/F0-parser^{commit}"),
            stdout="c0ffee\n",
        )
        tree = self.root / "cache" / "refs" / "oak" / "c0ffee"
        tree.mkdir(parents=True)
        self.processes.answer_entities(tree, "TASK", {"B13": (), "B9": ()}, ("MILESTONE==@MILESTONE.F0",))
        self.processes.answer_json(
            ("awawa", "status", "--json", str(self.config_root)),
            {"entities": [{"type": "REQUEST", "name": "oak_1", "file": "requests.awawa", "line": 1}]},
        )
        (self.config_root / "requests.awawa").write_text(
            "REQUEST oak_1\n\tPROJECT @PROJECT.oak\n\tSTATUS planned\n", encoding="utf-8"
        )
        self.processes.answer_corpus_change(
            self.config_root, ("requests.awawa",), "brigade wave start: @REQUEST.oak_1 running"
        )

    def test_should_start_the_first_wave_of_the_project_on_the_planned_request(self):
        # Arrange
        self.prepare_planned_request()

        # Act
        started = start_wave(self.runtime, Configuration(), "oak_1")

        # Assert
        self.assertEqual(
            started, {"request": "oak_1", "status": "running", "wave": "oak_w1", "milestone": "F0", "project": "oak"}
        )

    def test_should_mark_the_request_running(self):
        # Arrange
        self.prepare_planned_request()

        # Act
        start_wave(self.runtime, Configuration(), "oak_1")

        # Assert
        self.assertEqual(
            (self.config_root / "requests.awawa").read_text(encoding="utf-8"),
            "REQUEST oak_1\n\tPROJECT @PROJECT.oak\n\tSTATUS running\n",
        )

    def test_should_record_the_start_of_the_wave_with_its_tasks_in_their_order(self):
        # Arrange
        self.prepare_planned_request()

        # Act
        start_wave(self.runtime, Configuration(), "oak_1")

        # Assert
        line = json.loads((self.root / "state" / "ledger" / "2026-10.jsonl").read_text(encoding="utf-8"))
        self.assertEqual(
            line,
            {
                "schema_version": 2,
                "ts": "2026-10-19T09:00:00Z",
                "event": "wave.started",
                "wave": "oak_w1",
                "project": "oak",
                "branch": "integration/F0-parser",
                "tasks": ["B9", "B13"],
            },
        )

    def test_should_refuse_a_request_that_is_not_planned(self):
        # Arrange
        self.processes.answer_entity(
            self.config_root, "REQUEST", "oak_1", (("PROJECT", "@PROJECT.oak"), ("STATUS", "running"))
        )

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            start_wave(self.runtime, Configuration(), "oak_1")

        # Assert
        self.assertEqual(str(refusal.exception), "@REQUEST.oak_1 is running, not planned")
