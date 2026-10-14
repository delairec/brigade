import json
import unittest
from pathlib import Path

from tests.process_launcher import ProcessLauncher

CLONE_ENTRY_POINT = Path(__file__).resolve().parents[2] / "bin" / "brigade"


class BrigadeVersionTest(unittest.TestCase):
    def test_should_print_the_version(self):
        # Act
        completed = ProcessLauncher.run([CLONE_ENTRY_POINT, "--version"], capture_output=True, text=True, check=False)

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout, "brigade 0.1.0\n")


class BrigadeVersionWhenAJsonDocumentIsAskedTest(unittest.TestCase):
    def test_should_print_the_versioned_document(self):
        # Act
        completed = ProcessLauncher.run(
            [CLONE_ENTRY_POINT, "--version", "--json"], capture_output=True, text=True, check=False
        )

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout), {"schema_version": 1, "version": "0.1.0"})
