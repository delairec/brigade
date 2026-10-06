import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.cli.temporary_machine import TemporaryMachine

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


class BrigadeZipapp(unittest.TestCase):
    def setUp(self):
        self.clone = tempfile.TemporaryDirectory()
        clone_root = Path(self.clone.name)
        shutil.copytree(REPOSITORY_ROOT / "brigade", clone_root / "brigade", ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copy(REPOSITORY_ROOT / "build.py", clone_root / "build.py")
        subprocess.run([sys.executable, "build.py"], cwd=clone_root, check=True, stdout=subprocess.DEVNULL)

    def tearDown(self):
        self.clone.cleanup()

    def test_should_print_the_version_from_the_built_archive(self):
        # Act
        completed = subprocess.run([sys.executable, "dist/brigade.pyz", "--version"], capture_output=True, text=True, cwd=self.clone.name)

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
