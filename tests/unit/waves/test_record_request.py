import tempfile
import unittest
from pathlib import Path

from brigade.waves.record_request import NewRequest, record_request
from tests.unit.create_scripted_runtime import create_scripted_runtime
from tests.unit.scripted_processes import ScriptedProcesses


class RecordRequestTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.processes = ScriptedProcesses()
        self.runtime = create_scripted_runtime(Path(directory.name), self.processes)
        self.requests = self.runtime.paths.config_root / "requests.awawa"

    def test_should_write_the_first_request_of_the_operational_corpus_in_planning(self):
        # Arrange
        root = self.runtime.paths.config_root
        self.processes.answer_corpus_change(
            root, ("requests.awawa",), "brigade wave new: @REQUEST.oak_1 of @PROJECT.oak"
        )

        # Act
        name = record_request(self.runtime, NewRequest(project="oak", text='add a "parser"'))

        # Assert
        self.assertEqual(
            (name, self.requests.read_text(encoding="utf-8")),
            (
                "oak_1",
                (
                    "REQUEST oak_1\n"
                    "\tPROJECT @PROJECT.oak\n"
                    '\tTEXT "add a \\"parser\\""\n'
                    '\tCREATED_AT "2026-10-19T09:00:00Z"\n'
                    "\tSTATUS planning\n"
                ),
            ),
        )

    def test_should_append_the_next_request_of_the_project_after_the_recorded_ones(self):
        # Arrange
        self.requests.write_text("REQUEST oak_1\n\tSTATUS planned\n\n\n", encoding="utf-8")
        root = self.runtime.paths.config_root
        self.processes.answer_corpus_change(
            root, ("requests.awawa",), "brigade wave new: @REQUEST.oak_2 of @PROJECT.oak"
        )

        # Act
        name = record_request(self.runtime, NewRequest(project="oak", text="print"))

        # Assert
        self.assertEqual(
            (name, self.requests.read_text(encoding="utf-8")),
            (
                "oak_2",
                (
                    "REQUEST oak_1\n"
                    "\tSTATUS planned\n"
                    "\n"
                    "REQUEST oak_2\n"
                    "\tPROJECT @PROJECT.oak\n"
                    '\tTEXT "print"\n'
                    '\tCREATED_AT "2026-10-19T09:00:00Z"\n'
                    "\tSTATUS planning\n"
                ),
            ),
        )
