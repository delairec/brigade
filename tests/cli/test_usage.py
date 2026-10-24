import unittest
from pathlib import Path

from tests.process_launcher import ProcessLauncher

CLONE_ENTRY_POINT = Path(__file__).resolve().parents[2] / "bin" / "brigade"


class BrigadeUsageWhenNoOptionIsGivenTest(unittest.TestCase):
    def test_should_refuse_with_its_usage(self):
        # Act
        completed = ProcessLauncher.run([CLONE_ENTRY_POINT], capture_output=True, text=True, check=False)

        # Assert
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(completed.stdout, "")
        self.assertIn("usage: brigade", completed.stderr)
