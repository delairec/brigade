import tempfile
import unittest
from pathlib import Path

from tests.guards.find_subprocess_launches import find_subprocess_launches

TESTS_ROOT = Path(__file__).resolve().parents[1]


class SubprocessLaunchesOfTheTestsTest(unittest.TestCase):
    def test_should_find_no_launch_of_a_subprocess_outside_the_process_launcher(self):
        # Act
        violations = find_subprocess_launches(TESTS_ROOT)

        # Assert
        self.assertEqual(violations, [])


class SubprocessLaunchesGuardTest(unittest.TestCase):
    def test_should_flag_a_launch_of_a_subprocess_outside_the_process_launcher(self):
        # Arrange
        rows = [
            (
                "tests/cli/test_runs.py",
                "import subprocess\nsubprocess.run(['true'], check=False)\n",
                "tests/cli/test_runs.py:2 launches subprocess.run",
            ),
            (
                "tests/unit/test_stop.py",
                "import subprocess\nsubprocess.Popen(['sleep', '5'])\n",
                "tests/unit/test_stop.py:2 launches subprocess.Popen",
            ),
            (
                "tests/unit/test_stop.py",
                "import os\nimport subprocess as process\nprocess.Popen(argv)\n",
                "tests/unit/test_stop.py:3 launches subprocess.Popen",
            ),
            (
                "tests/unit/test_stop.py",
                "from subprocess import PIPE, Popen\n",
                "tests/unit/test_stop.py:1 imports subprocess.Popen",
            ),
            (
                "tests/cli/process_launcher.py",
                "import subprocess\nsubprocess.run(argv, check=False)\n",
                "tests/cli/process_launcher.py:2 launches subprocess.run",
            ),
        ]
        for module_path, source, expected_violation in rows:
            with self.subTest(module=module_path, source=source), tempfile.TemporaryDirectory() as root:
                # Arrange
                module = Path(root) / module_path
                module.parent.mkdir(parents=True)
                module.write_text(source)

                # Act
                violations = find_subprocess_launches(Path(root) / "tests")

                # Assert
                self.assertEqual(violations, [expected_violation])

    def test_should_let_the_process_launcher_launch_and_any_module_read_the_subprocess_constants(self):
        # Arrange
        rows = [
            ("tests/process_launcher.py", "import subprocess\nsubprocess.Popen(argv)\n"),
            ("tests/cli/test_runs.py", "import subprocess\nstart(argv, stdout=subprocess.PIPE)\n"),
            ("tests/cli/test_corpus.py", "from subprocess import TimeoutExpired\n"),
            ("tests/cli/test_tick.py", "import subprocess\ndef start_loop() -> subprocess.Popen: ...\n"),
        ]
        for module_path, source in rows:
            with self.subTest(module=module_path, source=source), tempfile.TemporaryDirectory() as root:
                # Arrange
                module = Path(root) / module_path
                module.parent.mkdir(parents=True)
                module.write_text(source)

                # Act
                violations = find_subprocess_launches(Path(root) / "tests")

                # Assert
                self.assertEqual(violations, [])
