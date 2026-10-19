import tempfile
import unittest
from pathlib import Path

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.collectors.shell import collect
from brigade.errors import BrigadeError
from brigade.system.read_configuration import Configuration
from tests.unit.create_scripted_runtime import create_scripted_runtime
from tests.unit.scripted_processes import ScriptedProcesses

EQUIPMENT = CollectorEquipment(configuration=Configuration(), forge=None, forge_name="github")


def create_environment(parameters: str) -> dict:
    return {"BRIGADE_PROJECT_PATH": "/srv/oak", "BRIGADE_SINCE": "2026-10-01", "BRIGADE_PARAMS": parameters}


class ShellCollectorTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.processes = ScriptedProcesses()
        self.runtime = create_scripted_runtime(Path(directory.name), self.processes)

    def test_should_collect_the_lines_the_command_printed_in_the_project(self):
        # Arrange
        self.processes.answer(("printf", "oak\\nelm\\n"), stdout="oak\nelm\n")

        # Act
        document = collect(create_environment('{"command": "printf \'oak\\\\nelm\\\\n\'"}'), self.runtime, EQUIPMENT)

        # Assert
        self.assertEqual(
            (document, self.processes.requests[0].cwd),
            (
                {
                    "schema_version": 1,
                    "collector": "shell",
                    "collected_at": "2026-10-19T09:00:00Z",
                    "cache": False,
                    "summary": {"lines": 2},
                    "items": ["oak", "elm"],
                },
                "/srv/oak",
            ),
        )

    def test_should_report_a_command_that_failed_with_its_errors(self):
        # Arrange
        self.processes.answer(("cat", "flag"), exit_code=1, stderr="cat: flag: No such file or directory\n")

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            collect(create_environment('{"command": "cat flag"}'), self.runtime, EQUIPMENT)

        # Assert
        self.assertEqual(str(refusal.exception), "the command exited 1\ncat: flag: No such file or directory")

    def test_should_refuse_to_run_without_a_command(self):
        # Act
        with self.assertRaises(BrigadeError) as refusal:
            collect(create_environment("{}"), self.runtime, EQUIPMENT)

        # Assert
        self.assertEqual(str(refusal.exception), "the shell collector takes command=<line>")
