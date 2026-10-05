import subprocess
import unittest
from pathlib import Path

CLONE_ENTRY_POINT = Path(__file__).resolve().parents[2] / "bin" / "brigade"


class BrigadeUsageWhenNoOptionIsGiven(unittest.TestCase):
    def test_should_refuse_with_its_usage(self):
        # Act
        completed = subprocess.run([CLONE_ENTRY_POINT], capture_output=True, text=True)

        # Assert
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(completed.stdout, "")
        self.assertIn("usage: brigade", completed.stderr)


class BrigadeUsageWhenAnUnknownOptionIsGiven(unittest.TestCase):
    def test_should_refuse_naming_the_option(self):
        # Act
        completed = subprocess.run([CLONE_ENTRY_POINT, "--frobnicate"], capture_output=True, text=True)

        # Assert
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(completed.stdout, "")
        self.assertIn("unrecognized arguments: --frobnicate", completed.stderr)


class BrigadeUsageWhenOnlyTheJsonOptionIsGiven(unittest.TestCase):
    def test_should_refuse_as_when_no_option_is_given(self):
        # Act
        completed = subprocess.run([CLONE_ENTRY_POINT, "--json"], capture_output=True, text=True)

        # Assert
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(completed.stdout, "")
        self.assertIn("brigade: error: no option given", completed.stderr)
