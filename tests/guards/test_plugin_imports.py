import tempfile
import unittest
from pathlib import Path

from tests.guards.find_plugin_imports import find_plugin_imports

PACKAGE_ROOT = Path(__file__).resolve().parents[2] / "brigade"


class PluginImportsOfThePackageTest(unittest.TestCase):
    def test_should_find_no_static_import_of_a_plugin_package_from_outside_it(self):
        # Act
        violations = find_plugin_imports(PACKAGE_ROOT)

        # Assert
        self.assertEqual(violations, [])


class PluginImportsGuardTest(unittest.TestCase):
    def test_should_flag_a_static_import_of_a_plugin_package_from_outside_it(self):
        # Arrange
        rows = [
            (
                "brigade/commands/doctor.py",
                "from brigade.adapters.test_clients import fake\n",
                "brigade/commands/doctor.py:1 imports brigade.adapters.test_clients",
            ),
            (
                "brigade/system/collect.py",
                "import brigade.collectors.git\n",
                "brigade/system/collect.py:1 imports brigade.collectors.git",
            ),
            ("brigade/cli.py", "from brigade import outputs\n", "brigade/cli.py:1 imports brigade.outputs"),
            (
                "brigade/commands/lint.py",
                "import os\nfrom brigade.checks.lint import run\n",
                "brigade/commands/lint.py:2 imports brigade.checks.lint",
            ),
            (
                "brigade/commands/forge.py",
                "from ..adapters import forges\n",
                "brigade/commands/forge.py:1 imports brigade.adapters",
            ),
        ]
        for module_path, source, expected_violation in rows:
            with self.subTest(module=module_path, source=source), tempfile.TemporaryDirectory() as root:
                # Arrange
                module = Path(root) / module_path
                module.parent.mkdir(parents=True)
                module.write_text(source)

                # Act
                violations = find_plugin_imports(Path(root) / "brigade")

                # Assert
                self.assertEqual(violations, [expected_violation])

    def test_should_let_a_plugin_import_its_own_package_and_the_core_and_the_resolver_import_by_name(self):
        # Arrange
        rows = [
            (
                "brigade/adapters/test_clients/fake.py",
                "from brigade.adapters.clients import describe_unreadable_output\n",
            ),
            ("brigade/adapters/forges/github.py", "from brigade.system.run_process import ProcessRequest\n"),
            (
                "brigade/system/resolve_plugin.py",
                'import importlib\nimportlib.import_module("brigade.adapters.test_clients.fake")\n',
            ),
        ]
        for module_path, source in rows:
            with self.subTest(module=module_path), tempfile.TemporaryDirectory() as root:
                # Arrange
                module = Path(root) / module_path
                module.parent.mkdir(parents=True)
                module.write_text(source)

                # Act
                violations = find_plugin_imports(Path(root) / "brigade")

                # Assert
                self.assertEqual(violations, [])
