import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.cli.temporary_machine import TemporaryMachine
from tests.process_launcher import ProcessLauncher

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


class BrigadeZipappTest(unittest.TestCase):
    def setUp(self):
        self.clone = tempfile.TemporaryDirectory()
        clone_root = Path(self.clone.name)
        shutil.copytree(
            REPOSITORY_ROOT / "brigade", clone_root / "brigade", ignore=shutil.ignore_patterns("__pycache__")
        )
        shutil.copy(REPOSITORY_ROOT / "build.py", clone_root / "build.py")
        ProcessLauncher.run([sys.executable, "build.py"], cwd=clone_root, check=True, stdout=subprocess.DEVNULL)

    def tearDown(self):
        self.clone.cleanup()

    def test_should_print_the_version_from_the_built_archive(self):
        # Act
        completed = ProcessLauncher.run(
            [sys.executable, "dist/brigade.pyz", "--version"],
            capture_output=True,
            text=True,
            cwd=self.clone.name,
            check=False,
        )

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout, "brigade 0.1.0\n")

    def test_should_install_the_schema_the_clone_ships_from_the_built_archive(self):
        # Arrange
        clone_root = Path(self.clone.name)
        machine_root = clone_root / "machine"
        machine_root.mkdir()
        machine = TemporaryMachine(machine_root)

        # Act
        completed = machine.run_brigade(clone_root / "dist" / "brigade.pyz", "init")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            (machine.corpus / "_schema.awawa").read_bytes(),
            (clone_root / "brigade" / "corpus" / "data" / "schema.awawa.tpl").read_bytes(),
        )

    def test_should_answer_through_the_fake_adapter_the_built_archive_ships(self):
        # Arrange
        clone_root = Path(self.clone.name)
        machine_root = clone_root / "machine"
        machine_root.mkdir()
        machine = TemporaryMachine(machine_root)
        machine.write_configuration('client = "fake"\n')

        # Act
        completed = machine.run_brigade(clone_root / "dist" / "brigade.pyz", "adapter", "probe", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "client": "fake",
                "version_argv": None,
                "operations": ["probe", "launch", "result"],
                "features": [],
                "models": {},
            },
        )

    def test_should_print_the_built_in_role_the_built_archive_ships(self):
        # Arrange
        clone_root = Path(self.clone.name)
        machine_root = clone_root / "machine"
        machine_root.mkdir()
        machine = TemporaryMachine(machine_root)

        # Act
        completed = machine.run_brigade(clone_root / "dist" / "brigade.pyz", "roles", "show", "plan")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout, (clone_root / "brigade" / "roles" / "data" / "planner.md").read_text())

    def test_should_list_the_built_in_adapters_the_built_archive_ships_with_their_audience(self):
        # Arrange
        clone_root = Path(self.clone.name)
        machine_root = clone_root / "machine"
        machine_root.mkdir()
        directory_without_adapter = machine_root / "bin"
        directory_without_adapter.mkdir()
        machine = TemporaryMachine(machine_root)
        environment = {**machine.describe_environment(), "PATH": str(directory_without_adapter)}

        # Act
        completed = machine.run_brigade(
            clone_root / "dist" / "brigade.pyz", "adapter", "matrix", "--markdown", environment=environment
        )

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stdout,
            "| Supported client | Launch | Result | Resume | Transcripts | Actions | Step count | Tool grants | Reset hour | Graceful stop |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
            "| claude-code | full | full | full | full | full | full | full | full | full |\n"
            "| vibe | full | full | fallback | full | fallback | full | full | fallback | fallback |\n"
            "\n"
            "| Test-suite adapter | Launch | Result | Resume | Transcripts | Actions | Step count | Tool grants | Reset hour | Graceful stop |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
            "| fake | full | full | fallback | fallback | fallback | fallback | fallback | fallback | fallback |\n"
            "\n"
            "Fallbacks:\n"
            "\n"
            "- no resume: a fresh launch from the progress file\n"
            "- no transcripts: brigade's journal of the run\n"
            "- no actions: one raw record per line of the client's output\n"
            "- no step count: steps null and the run held on the clock alone\n"
            "- no tool grants: the client's unattended mode and a disposable worktree for a reading slot\n"
            "- no reset hour: now plus thirty minutes\n"
            "- no graceful stop: the hard cut at the wall-time limit\n",
        )
