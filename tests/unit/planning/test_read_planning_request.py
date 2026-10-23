import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.planning.read_planning_request import PlanningRequest, read_planning_request
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.scripted_processes import ScriptedProcesses


class ReadPlanningRequestTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.processes = ScriptedProcesses()
        write_operational_corpus(Path(directory.name))
        self.runtime = create_test_runtime(create_test_paths(Path(directory.name)), run_process=self.processes)

    def test_should_read_the_project_and_the_text_of_a_request_in_planning(self):
        # Arrange
        self.processes.answer_entity(
            self.runtime.paths.config_root,
            "REQUEST",
            "oak_1",
            (("PROJECT", "@PROJECT.oak"), ("TEXT", "print"), ("STATUS", "planning")),
        )

        # Act
        request = read_planning_request(self.runtime, "oak_1")

        # Assert
        self.assertEqual(request, PlanningRequest(name="oak_1", project="oak", text="print"))

    def test_should_refuse_a_request_no_longer_in_planning(self):
        # Arrange
        self.processes.answer_entity(
            self.runtime.paths.config_root, "REQUEST", "oak_1", (("PROJECT", "@PROJECT.oak"), ("STATUS", "planned"))
        )

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            read_planning_request(self.runtime, "oak_1")

        # Assert
        self.assertEqual(str(refusal.exception), "@REQUEST.oak_1 is planned, not planning")
