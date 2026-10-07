import unittest
from types import SimpleNamespace

from brigade.errors import BrigadeError
from brigade.system.resolve_plugin import resolve_plugin

NO_RUNTIME_NEEDED = None


class ResolvePluginRefusalTest(unittest.TestCase):
    def test_should_refuse_a_client_name_no_adapter_can_carry(self):
        # Arrange
        runtime = SimpleNamespace(paths=SimpleNamespace(executable_search_path=""))

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            resolve_plugin("client", "claude.code", runtime)

        # Assert
        self.assertEqual(
            str(refusal.exception),
            "no client adapter claude.code: no built-in module and no brigade-client-claude.code on PATH",
        )

    def test_should_refuse_a_built_in_plugin_brigade_does_not_ship(self):
        # Act
        with self.assertRaises(BrigadeError) as refusal:
            resolve_plugin("forge", "gitlab", NO_RUNTIME_NEEDED)

        # Assert
        self.assertEqual(str(refusal.exception), "no forge plugin gitlab")

    def test_should_refuse_a_kind_of_plugin_brigade_does_not_know(self):
        # Act
        with self.assertRaises(BrigadeError) as refusal:
            resolve_plugin("collector", "github", NO_RUNTIME_NEEDED)

        # Assert
        self.assertEqual(str(refusal.exception), "no plugin kind collector")
