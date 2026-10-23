import tempfile
import unittest
from pathlib import Path

from tests.guards.find_clock_reads import find_clock_reads

PACKAGE_ROOT = Path(__file__).resolve().parents[2] / "brigade"


class ClockReadsOfThePackageTest(unittest.TestCase):
    def test_should_find_no_clock_read_outside_the_system_package_and_the_runtime(self):
        # Act
        violations = find_clock_reads(PACKAGE_ROOT)

        # Assert
        self.assertEqual(violations, [])


class ClockReadsGuardTest(unittest.TestCase):
    def test_should_flag_a_clock_read_outside_the_system_package_and_the_runtime(self):
        # Arrange
        rows = [
            ("import time\nstarted = time.monotonic()\n", "brigade/commands/tick.py:2 reads time.monotonic"),
            ("from time import monotonic\nmonotonic()\n", "brigade/commands/tick.py:2 reads time.monotonic"),
            ("at = datetime.now(UTC)\n", "brigade/commands/tick.py:1 reads datetime.now"),
            ("import datetime\nat = datetime.datetime.now()\n", "brigade/commands/tick.py:2 reads datetime.now"),
        ]
        for source, expected_violation in rows:
            with self.subTest(source=source), tempfile.TemporaryDirectory() as root:
                # Arrange
                module = Path(root) / "brigade" / "commands" / "tick.py"
                module.parent.mkdir(parents=True)
                module.write_text(source)

                # Act
                violations = find_clock_reads(Path(root) / "brigade")

                # Assert
                self.assertEqual(violations, [expected_violation])

    def test_should_let_the_system_package_and_the_runtime_read_the_clock(self):
        # Arrange
        rows = ["brigade/runtime.py", "brigade/system/wait_within_limit.py"]
        for module_path in rows:
            with self.subTest(module=module_path), tempfile.TemporaryDirectory() as root:
                # Arrange
                module = Path(root) / module_path
                module.parent.mkdir(parents=True, exist_ok=True)
                module.write_text("import time\ntime.monotonic()\nat = datetime.now(UTC)\n")

                # Act
                violations = find_clock_reads(Path(root) / "brigade")

                # Assert
                self.assertEqual(violations, [])
