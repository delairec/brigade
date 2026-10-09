import tempfile
import unittest
from pathlib import Path

from tests.guards.find_configuration_reads import find_configuration_reads

PACKAGE_ROOT = Path(__file__).resolve().parents[2] / "brigade"


class ConfigurationReadsOfThePackageTest(unittest.TestCase):
    def test_should_find_no_configuration_read_outside_the_commands_and_the_readers(self):
        # Act
        violations = find_configuration_reads(PACKAGE_ROOT)

        # Assert
        self.assertEqual(violations, [])


class ConfigurationReadsGuardTest(unittest.TestCase):
    def test_should_flag_a_configuration_read_below_the_commands(self):
        rows = [
            (
                "brigade/roles/resolve_role.py",
                "configuration = read_optional_configuration(path)\n",
                "brigade/roles/resolve_role.py:1 calls read_optional_configuration",
            ),
            (
                "brigade/runs/read_run_setting.py",
                "import os\nconfiguration = read_configuration(path)\n",
                "brigade/runs/read_run_setting.py:2 calls read_configuration",
            ),
            (
                "brigade/system/ask_named_client.py",
                "configured = reading.read_configured_client(runtime)\n",
                "brigade/system/ask_named_client.py:1 calls read_configured_client",
            ),
            (
                "brigade/cli.py",
                "configuration = read_configuration(runtime.paths.configuration_file)\n",
                "brigade/cli.py:1 calls read_configuration",
            ),
        ]
        for module_path, source, expected_violation in rows:
            with self.subTest(module=module_path), tempfile.TemporaryDirectory() as root:
                # Arrange
                module = Path(root) / module_path
                module.parent.mkdir(parents=True)
                module.write_text(source)

                # Act
                violations = find_configuration_reads(Path(root) / "brigade")

                # Assert
                self.assertEqual(violations, [expected_violation])

    def test_should_let_the_commands_and_the_readers_read(self):
        rows = [
            ("brigade/commands/doctor.py", "configuration = read_configuration(runtime.paths.configuration_file)\n"),
            ("brigade/system/read_optional_configuration.py", "configuration = read_configuration(path)\n"),
            ("brigade/system/read_configured_client.py", "configuration = read_configuration(path)\n"),
            ("brigade/system/read_configuration.py", "configuration = read_configuration(path)\n"),
        ]
        for module_path, source in rows:
            with self.subTest(module=module_path), tempfile.TemporaryDirectory() as root:
                # Arrange
                module = Path(root) / module_path
                module.parent.mkdir(parents=True)
                module.write_text(source)

                # Act
                violations = find_configuration_reads(Path(root) / "brigade")

                # Assert
                self.assertEqual(violations, [])

    def test_should_let_the_purge_of_the_trails_parse_config_toml_itself(self):
        # Arrange
        purge_source = "document = tomllib.loads(paths.configuration_file.read_text())\n"
        with tempfile.TemporaryDirectory() as root:
            module = Path(root) / "brigade/system/remove_expired_trails.py"
            module.parent.mkdir(parents=True)
            module.write_text(purge_source)

            # Act
            violations = find_configuration_reads(Path(root) / "brigade")

        # Assert
        self.assertEqual(violations, [])
