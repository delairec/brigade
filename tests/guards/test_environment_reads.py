import tempfile
import unittest
from pathlib import Path

from tests.guards.find_environment_reads import find_environment_reads

PACKAGE_ROOT = Path(__file__).resolve().parents[2] / "brigade"


class EnvironmentReadsOfThePackageTest(unittest.TestCase):
    def test_should_find_no_read_of_the_environment_outside_the_paths_and_the_process_runner(self):
        # Act
        violations = find_environment_reads(PACKAGE_ROOT)

        # Assert
        self.assertEqual(violations, [])


class EnvironmentReadsGuardTest(unittest.TestCase):
    def test_should_flag_each_way_of_reading_the_environment(self):
        # Arrange
        rows = [
            ("import os\nhome = os.environ['HOME']\n", "brigade/commands/doctor.py:2 reads os.environ"),
            ("import os\nhome = os.environ.get('HOME')\n", "brigade/commands/doctor.py:2 reads os.environ"),
            ("import os\nhome = os.getenv('HOME')\n", "brigade/commands/doctor.py:2 reads os.getenv"),
            ("from os import environ\n", "brigade/commands/doctor.py:1 reads os.environ"),
            ("from os import getenv\n", "brigade/commands/doctor.py:1 reads os.getenv"),
            ("from pathlib import Path\nhome = Path.home()\n", "brigade/commands/doctor.py:2 reads Path.home"),
            ("import os\nhome = os.path.expanduser('~')\n", "brigade/commands/doctor.py:2 reads expanduser"),
            (
                "from pathlib import Path\nhome = Path('~').expanduser()\n",
                "brigade/commands/doctor.py:2 reads expanduser",
            ),
        ]
        for source, expected_violation in rows:
            with self.subTest(source=source), tempfile.TemporaryDirectory() as root:
                # Arrange
                module = Path(root) / "brigade" / "commands" / "doctor.py"
                module.parent.mkdir(parents=True)
                module.write_text(source)

                # Act
                violations = find_environment_reads(Path(root) / "brigade")

                # Assert
                self.assertEqual(violations, [expected_violation])

    def test_should_let_the_paths_and_the_process_runner_read_the_environment(self):
        # Arrange
        rows = [
            "brigade/system/paths.py",
            "brigade/system/run_process.py",
            "brigade/system/build_process_environment.py",
        ]
        for module_path in rows:
            with self.subTest(module=module_path), tempfile.TemporaryDirectory() as root:
                # Arrange
                module = Path(root) / module_path
                module.parent.mkdir(parents=True)
                module.write_text("import os\nfrom pathlib import Path\nhome = os.environ.get('HOME') or Path.home()\n")

                # Act
                violations = find_environment_reads(Path(root) / "brigade")

                # Assert
                self.assertEqual(violations, [])
