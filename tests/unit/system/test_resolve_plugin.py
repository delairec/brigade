import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.system.collector_places import CollectorPlaces
from brigade.system.resolve_plugin import ClientExecutableCaller, PluginSources, resolve_plugin
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner
from tests.unit.refuse_to_run import refuse_to_run

NO_SOURCES_NEEDED = None
NO_EXECUTABLE_DIRECTORY = ""


class ResolvePluginRefusalTest(unittest.TestCase):
    def test_should_refuse_a_client_name_no_adapter_can_carry(self):
        # Arrange
        sources = PluginSources(executable_search_path=NO_EXECUTABLE_DIRECTORY, run_process=refuse_to_run)

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

    def test_should_refuse_a_scheduler_brigade_does_not_ship(self):
        # Arrange
        rows = [
            ("launchd", "no scheduler plugin launchd"),
            ("data", "no scheduler plugin data"),
            ("__init__", "no scheduler plugin __init__"),
        ]
        for name, expected_refusal in rows:
            with self.subTest(name=name):
                # Act
                with self.assertRaises(BrigadeError) as refusal:
                    resolve_plugin("scheduler", name, NO_SOURCES_NEEDED)

                # Assert
                self.assertEqual(str(refusal.exception), expected_refusal)

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

    def test_should_refuse_a_client_found_neither_among_the_modules_nor_on_path(self):
        # Arrange
        sources = PluginSources(executable_search_path=NO_EXECUTABLE_DIRECTORY, run_process=refuse_to_run)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            resolve_plugin("client", "frobnicate", sources)

        # Assert
        self.assertEqual(
            str(refusal.exception),
            "no client adapter frobnicate: no built-in module and no brigade-client-frobnicate on PATH",
        )

    def test_should_not_take_a_helper_module_of_the_adapters_for_a_client_adapter(self):
        # Arrange
        sources = PluginSources(executable_search_path=NO_EXECUTABLE_DIRECTORY, run_process=refuse_to_run)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            resolve_plugin("client", "describe-unreadable-output", sources)

        # Assert
        self.assertEqual(
            str(refusal.exception),
            "no client adapter describe-unreadable-output: no built-in module and no"
            " brigade-client-describe-unreadable-output on PATH",
        )


class ResolvePluginOfAnExecutableClientTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.executable = Path(self.root.name) / "brigade-client-scripted"
        self.executable.write_text("#!/bin/sh\n")
        self.executable.chmod(0o755)

    def test_should_answer_through_the_executable_of_the_client_on_path(self):
        # Arrange
        sources = PluginSources(executable_search_path=self.root.name, run_process=refuse_to_run)

        # Act
        client = resolve_plugin("client", "scripted", sources)

        # Assert
        self.assertEqual(
            client,
            ClientExecutableCaller(name="scripted", executable=str(self.executable), run_process=refuse_to_run),
        )


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
