import json
import sys
import tempfile
import unittest
from pathlib import Path

from tests.cli.temporary_machine import REPOSITORY_ROOT, TemporaryMachine
from tests.process_launcher import ProcessLauncher

REPORTING_MODULE = "tests.cli.report_command_imports"


class CommandImportsTestCase(unittest.TestCase):
    def setUp(self):
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        self.root = Path(root.name).resolve()
        self.machine = TemporaryMachine(self.root)

    def run_listing_command_imports(self, *arguments: str) -> list[str]:
        report = self.root / "command-imports.json"
        completed = ProcessLauncher.run(
            [sys.executable, "-m", REPORTING_MODULE, str(report), *arguments],
            capture_output=True,
            text=True,
            env=self.machine.describe_environment(),
            cwd=REPOSITORY_ROOT,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(report.read_text())


class BrigadeVersionImportsTest(CommandImportsTestCase):
    def test_should_import_no_command_module(self):
        # Act
        imported = self.run_listing_command_imports("--version")

        # Assert
        self.assertEqual(imported, [])


class BrigadeCommandLineImportsTest(CommandImportsTestCase):
    def test_should_import_the_module_of_the_command_line_alone(self):
        # Act
        imported = self.run_listing_command_imports("runs", "list")

        # Assert
        self.assertEqual(imported, ["brigade.commands.runs_list"])
