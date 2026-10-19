import argparse
import tempfile
import unittest
from pathlib import Path

from brigade.commands.adapter_probe import COMMAND, adapter_probe
from brigade.system.ask_configured_client import ConfiguredClientAnswer
from tests.unit.commands.create_command_runtime import create_command_runtime
from tests.unit.commands.create_plugin_resolver import ScriptedClient, create_plugin_resolver

PROBE_ANSWER = {
    "schema_version": 1,
    "client": "scripted",
    "version_argv": None,
    "operations": ["probe", "launch", "result"],
    "features": [],
    "models": {},
}


class AdapterProbeTextTest(unittest.TestCase):
    def test_should_print_the_answer_of_the_adapter_as_indented_json(self):
        # Arrange
        document = {"schema_version": 1, "client": "scripted"}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, '{\n  "schema_version": 1,\n  "client": "scripted"\n}')


class AdapterProbeRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_they_are(self):
        # Arrange
        options = argparse.Namespace(json=True)

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertEqual(request, argparse.Namespace(json=True))


class AdapterProbeExitCodeTest(unittest.TestCase):
    def test_should_exit_0_once_the_adapter_answered(self):
        # Act
        exit_code = COMMAND.decide_exit_code(PROBE_ANSWER)

        # Assert
        self.assertEqual(exit_code, 0)


class AdapterProbeOfTheConfiguredClientTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        client = ScriptedClient({"probe": PROBE_ANSWER})
        self.runtime = create_command_runtime(
            Path(self.root.name), resolve_plugin=create_plugin_resolver({("client", "scripted"): client})
        )
        self.runtime.paths.config_root.mkdir(parents=True)
        self.runtime.paths.configuration_file.write_text('client = "scripted"\n')

    def test_should_answer_the_probe_of_the_configured_client(self):
        # Arrange
        no_option = argparse.Namespace()

        # Act
        answer = adapter_probe(no_option, self.runtime)

        # Assert
        self.assertEqual(answer, ConfiguredClientAnswer(client="scripted", slot_clients={}, document=PROBE_ANSWER))
