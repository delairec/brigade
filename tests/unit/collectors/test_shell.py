import tempfile
import unittest
from pathlib import Path

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.collectors.shell import collect
from brigade.errors import BrigadeError
from brigade.system.parse_configuration import Configuration
from brigade.system.run_process import EVERY_EXIT_CODE, ProcessRequest
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.scripted_processes import ScriptedProcesses

EQUIPMENT = CollectorEquipment(configuration=Configuration(), forge=None, forge_name="github")


def create_environment(parameters: str) -> dict:
    return {"BRIGADE_PROJECT_PATH": "/srv/oak", "BRIGADE_SINCE": "2026-10-01", "BRIGADE_PARAMS": parameters}


class ShellCollectorTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.processes = ScriptedProcesses()
        write_operational_corpus(Path(directory.name))
        self.runtime = create_test_runtime(create_test_paths(Path(directory.name)), run_process=self.processes)

    def test_should_collect_the_lines_the_command_printed(self):
        # Arrange
        self.processes.answer(("printf", "oak\\nelm\\n"), stdout="oak\nelm\n")

        # Act
        document = collect(create_environment('{"command": "printf \'oak\\\\nelm\\\\n\'"}'), self.runtime, EQUIPMENT)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "collector": "shell",
                "collected_at": "2026-10-19T09:00:00Z",
                "cache": False,
                "summary": {"lines": 2},
                "items": ["oak", "elm"],
            },
        )

    def test_should_run_the_command_in_the_project(self):
        # Arrange
        self.processes.answer(("ls",), stdout="README.md\n")

        # Act
        collect(create_environment('{"command": "ls"}'), self.runtime, EQUIPMENT)

        # Assert
        self.assertEqual(
            self.processes.requests,
            [
                ProcessRequest(
                    argv=("ls",),
                    cwd="/srv/oak",
                    timeout_s=600.0,
                    acceptable_exit_codes=EVERY_EXIT_CODE,
                    stdin=None,
                )
            ],
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
        for parameters in ["{}", '{"command": ""}']:
            with self.subTest(parameters=parameters):
                # Act
                with self.assertRaises(BrigadeError) as refusal:
                    collect(create_environment(parameters), self.runtime, EQUIPMENT)

                # Assert
                self.assertEqual(str(refusal.exception), "the shell collector takes command=<line>")
