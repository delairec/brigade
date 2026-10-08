import tempfile
import unittest
from pathlib import Path

from tests.guards.find_resolver_calls import find_resolver_calls

PACKAGE_ROOT = Path(__file__).resolve().parents[2] / "brigade"


class ResolverCallsOfThePackageTest(unittest.TestCase):
    def test_should_find_no_plugin_resolved_outside_the_command_line_and_the_commands(self):
        # Act
        violations = find_resolver_calls(PACKAGE_ROOT)

        # Assert
        self.assertEqual(violations, [])


class ResolverCallsGuardTest(unittest.TestCase):
    def test_should_flag_a_plugin_resolved_by_a_core_module(self):
        rows = [
            (
                "brigade/system/ask_named_client.py",
                'client = resolve_plugin("client", name, sources)\n',
                "brigade/system/ask_named_client.py:1 calls resolve_plugin",
            ),
            (
                "brigade/runs/run_segment.py",
                'import os\nclient = runtime.resolve_plugin("client", plan.client)\n',
                "brigade/runs/run_segment.py:2 calls resolve_plugin",
            ),
            (
                "brigade/adapters/forges/github.py",
                'scheduler = runtime.resolve_plugin("scheduler", "cron")\n',
                "brigade/adapters/forges/github.py:1 calls resolve_plugin",
            ),
        ]
        for module_path, source, expected_violation in rows:
            with self.subTest(module=module_path), tempfile.TemporaryDirectory() as root:
                # Arrange
                module = Path(root) / module_path
                module.parent.mkdir(parents=True)
                module.write_text(source)

                # Act
                violations = find_resolver_calls(Path(root) / "brigade")

                # Assert
                self.assertEqual(violations, [expected_violation])

    def test_should_let_the_command_line_the_runtime_and_the_commands_resolve(self):
        rows = [
            ("brigade/cli.py", 'forge = runtime.resolve_plugin("forge", "github")\n'),
            ("brigade/runtime.py", "resolver = functools.partial(resolve_plugin, sources=sources)\n"),
            ("brigade/commands/doctor.py", 'forge = runtime.resolve_plugin("forge", "github")\n'),
            ("brigade/system/resolve_plugin.py", "def resolve_plugin(kind, name, sources):\n    return None\n"),
        ]
        for module_path, source in rows:
            with self.subTest(module=module_path), tempfile.TemporaryDirectory() as root:
                # Arrange
                module = Path(root) / module_path
                module.parent.mkdir(parents=True)
                module.write_text(source)

                # Act
                violations = find_resolver_calls(Path(root) / "brigade")

                # Assert
                self.assertEqual(violations, [])
