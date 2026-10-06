import tempfile
import unittest
from pathlib import Path

from tests.guards.find_subprocess_uses import find_subprocess_uses

PACKAGE_ROOT = Path(__file__).resolve().parents[2] / "brigade"


class SubprocessUsesOfThePackage(unittest.TestCase):
    def test_should_find_no_subprocess_import_outside_the_system_package_and_no_shell_anywhere(self):
        # Act
        violations = find_subprocess_uses(PACKAGE_ROOT)

        # Assert
        self.assertEqual(violations, [])


class SubprocessUsesGuard(unittest.TestCase):
    def test_should_flag_a_subprocess_import_outside_the_system_package_and_a_shell_anywhere(self):
        rows = [
            ("brigade/commands/doctor.py", "import subprocess\n", "brigade/commands/doctor.py:1 imports subprocess"),
            ("brigade/commands/doctor.py", "import os\nimport subprocess as process\n", "brigade/commands/doctor.py:2 imports subprocess"),
            ("brigade/commands/doctor.py", "from subprocess import run\n", "brigade/commands/doctor.py:1 imports subprocess"),
            ("brigade/systemd/write_units.py", "import subprocess\n", "brigade/systemd/write_units.py:1 imports subprocess"),
            ("brigade/system/run_process.py", "import subprocess\nsubprocess.run('ls', shell=True)\n", "brigade/system/run_process.py:2 passes shell=True"),
            ("brigade/system/run_process.py", "import subprocess\nsubprocess.run(argv, shell=use_shell)\n", "brigade/system/run_process.py:2 passes shell=use_shell"),
            ("brigade/cli.py", "from brigade.system.spawn_process import spawn_process\nspawn_process(request, shell=True)\n", "brigade/cli.py:2 passes shell=True"),
        ]
        for module_path, source, expected_violation in rows:
            with self.subTest(module=module_path, source=source):
                with tempfile.TemporaryDirectory() as root:
                    # Arrange
                    module = Path(root) / module_path
                    module.parent.mkdir(parents=True)
                    module.write_text(source)

                    # Act
                    violations = find_subprocess_uses(Path(root) / "brigade")

                    # Assert
                    self.assertEqual(violations, [expected_violation])

    def test_should_let_the_system_package_import_subprocess_without_a_shell(self):
        rows = [
            ("brigade/system/run_process.py", "import subprocess\nsubprocess.run(argv, shell=False)\n"),
            ("brigade/system/process/wait_within_limit.py", "from subprocess import Popen, TimeoutExpired\n"),
        ]
        for module_path, source in rows:
            with self.subTest(module=module_path, source=source):
                with tempfile.TemporaryDirectory() as root:
                    # Arrange
                    module = Path(root) / module_path
                    module.parent.mkdir(parents=True)
                    module.write_text(source)

                    # Act
                    violations = find_subprocess_uses(Path(root) / "brigade")

                    # Assert
                    self.assertEqual(violations, [])
