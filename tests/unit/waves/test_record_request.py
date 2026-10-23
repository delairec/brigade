import tempfile
import unittest
from pathlib import Path

from brigade.waves.record_request import NewRequest, record_request
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.scripted_processes import ScriptedProcesses


class RecordRequestTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.processes = ScriptedProcesses()
        write_operational_corpus(Path(directory.name))
        self.runtime = create_test_runtime(create_test_paths(Path(directory.name)), run_process=self.processes)
        self.config_root = self.runtime.paths.config_root
        self.requests = self.config_root / "requests.awawa"

    def test_should_name_the_first_request_of_the_project_one(self):
        # Arrange
        message = "brigade request new: @REQUEST.oak_r1 of @PROJECT.oak"
        self.processes.answer_corpus_change(self.config_root, ("requests.awawa",), message)

        # Act
        name = record_request(self.runtime, NewRequest(project="oak", text="print"))

        # Assert
        self.assertEqual(name, "oak_r1")

    def test_should_write_the_first_request_of_the_operational_corpus_in_planning(self):
        # Arrange
        message = "brigade request new: @REQUEST.oak_r1 of @PROJECT.oak"
        self.processes.answer_corpus_change(self.config_root, ("requests.awawa",), message)

        # Act
        record_request(self.runtime, NewRequest(project="oak", text='add a "parser"'))

        # Assert
        self.assertEqual(
            self.requests.read_text(encoding="utf-8"),
            "REQUEST oak_r1\n"
            "\tPROJECT @PROJECT.oak\n"
            '\tTEXT "add a \\"parser\\""\n'
            '\tCREATED_AT "2026-10-19T09:00:00Z"\n'
            "\tSTATUS planning\n",
        )

    def test_should_name_the_next_request_after_the_recorded_ones(self):
        # Arrange
        self.requests.write_text("REQUEST oak_r1\n\tSTATUS planned\n\n\n", encoding="utf-8")
        message = "brigade request new: @REQUEST.oak_r2 of @PROJECT.oak"
        self.processes.answer_corpus_change(self.config_root, ("requests.awawa",), message)

        # Act
        name = record_request(self.runtime, NewRequest(project="oak", text="print"))

        # Assert
        self.assertEqual(name, "oak_r2")

    def test_should_append_the_next_request_after_the_recorded_ones(self):
        # Arrange
        self.requests.write_text("REQUEST oak_r1\n\tSTATUS planned\n\n\n", encoding="utf-8")
        message = "brigade request new: @REQUEST.oak_r2 of @PROJECT.oak"
        self.processes.answer_corpus_change(self.config_root, ("requests.awawa",), message)

        # Act
        record_request(self.runtime, NewRequest(project="oak", text="print"))

        # Assert
        self.assertEqual(
            self.requests.read_text(encoding="utf-8"),
            "REQUEST oak_r1\n"
            "\tSTATUS planned\n"
            "\n"
            "REQUEST oak_r2\n"
            "\tPROJECT @PROJECT.oak\n"
            '\tTEXT "print"\n'
            '\tCREATED_AT "2026-10-19T09:00:00Z"\n'
            "\tSTATUS planning\n",
        )
