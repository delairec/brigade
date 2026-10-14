import unittest

from brigade.errors import BrigadeError
from brigade.system.resolve_plugin import PluginSources, resolve_plugin

NO_SOURCES_NEEDED = None
NO_EXECUTABLE_DIRECTORY = ""


def _refuse_process(request):
    raise AssertionError(f"the resolver ran {request.argv}")


class ResolvePluginRefusalTest(unittest.TestCase):
    def test_should_refuse_a_client_name_no_adapter_can_carry(self):
        # Arrange
        sources = PluginSources(executable_search_path=NO_EXECUTABLE_DIRECTORY, run_process=_refuse_process)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            resolve_plugin("client", "claude.code", sources)

        # Assert
        self.assertEqual(
            str(refusal.exception),
            "no client adapter claude.code: no built-in module and no brigade-client-claude.code on PATH",
        )

    def test_should_refuse_a_built_in_plugin_brigade_does_not_ship(self):
        # Act
        with self.assertRaises(BrigadeError) as refusal:
            resolve_plugin("forge", "gitlab", NO_SOURCES_NEEDED)

        # Assert
        self.assertEqual(str(refusal.exception), "no forge plugin gitlab")

    def test_should_refuse_a_document_plugin_brigade_does_not_ship(self):
        # Act
        with self.assertRaises(BrigadeError) as refusal:
            resolve_plugin("document", "yaml", NO_SOURCES_NEEDED)

        # Assert
        self.assertEqual(str(refusal.exception), "no document plugin yaml")

    def test_should_refuse_a_kind_of_plugin_brigade_does_not_know(self):
        # Act
        with self.assertRaises(BrigadeError) as refusal:
            resolve_plugin("collector", "github", NO_SOURCES_NEEDED)

        # Assert
        self.assertEqual(str(refusal.exception), "no plugin kind collector")
