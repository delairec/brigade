import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.system.collector_places import CollectorPlaces
from brigade.system.resolve_plugin import ClientExecutableCaller, PluginSources, resolve_plugin
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

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
            resolve_plugin("check", "github", NO_SOURCES_NEEDED)

        # Assert
        self.assertEqual(str(refusal.exception), "no plugin kind check")


class ResolvePluginOfACollectorTest(unittest.TestCase):
    def test_should_resolve_the_collector_among_its_places(self):
        # Arrange
        places = CollectorPlaces(
            project_directory=Path("/nonexistent/shop/.brigade/collectors"),
            machine_directory=Path("/nonexistent/config/collectors"),
            executable_search_path=NO_EXECUTABLE_DIRECTORY,
        )

        # Act
        collector = resolve_plugin("collector", "pr-list", NO_SOURCES_NEEDED, places)

        # Assert
        self.assertEqual(collector.source, "built-in")


class ClientExecutableCallerTest(unittest.TestCase):
    def test_should_refuse_an_answer_that_is_no_json_document(self):
        # Arrange
        caller = ClientExecutableCaller(
            name="local",
            executable="/usr/local/bin/brigade-client-local",
            run_process=RecordingProcessRunner(
                {("/usr/local/bin/brigade-client-local", "probe"): ProcessAnswer(stdout="Usage: local\n")}
            ),
        )

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            caller.answer("probe", {"schema_version": 1})

        # Assert
        self.assertEqual(str(refusal.exception), "client adapter local answered probe with no JSON document")
