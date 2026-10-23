import argparse
import io
import tempfile
import unittest
from pathlib import Path

from brigade.commands.adapter_actions import COMMAND, adapter_actions
from brigade.system.ask_configured_client import ConfiguredClientAnswer
from tests.unit.commands.create_plugin_resolver import ScriptedClient, create_plugin_resolver
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

ACTIONS_REQUEST = '{"schema_version": 1, "output": "Reading."}'
ACTIONS_ANSWER = {"schema_version": 1, "actions": [{"kind": "text", "summary": "Reading."}]}


class AdapterActionsTextTest(unittest.TestCase):
    def test_should_print_the_answer_of_the_adapter_as_indented_json(self):
        # Arrange
        document = {"schema_version": 1, "actions": []}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, '{\n  "schema_version": 1,\n  "actions": []\n}')


class AdapterActionsRequestTest(unittest.TestCase):
    def test_should_read_the_request_on_stdin(self):
        # Arrange
        options = argparse.Namespace(standard_input=io.StringIO(ACTIONS_REQUEST))

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertEqual(request, ACTIONS_REQUEST)


class AdapterActionsExitCodeTest(unittest.TestCase):
    def test_should_exit_0_once_the_adapter_answered(self):
        # Act
        exit_code = COMMAND.decide_exit_code(ACTIONS_ANSWER)

        # Assert
        self.assertEqual(exit_code, 0)


class AdapterActionsOfTheConfiguredClientTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        client = ScriptedClient({"actions": ACTIONS_ANSWER})
        self.runtime = create_test_runtime(
            create_test_paths(Path(self.root.name)),
            resolve_plugin=create_plugin_resolver({("client", "scripted"): client}),
        )
        self.runtime.paths.config_root.mkdir(parents=True)
        self.runtime.paths.configuration_file.write_text('client = "scripted"\n')

    def test_should_answer_the_actions_the_configured_client_reads_in_the_output(self):
        # Act
        answer = adapter_actions(ACTIONS_REQUEST, self.runtime)

        # Assert
        self.assertEqual(answer, ConfiguredClientAnswer(client="scripted", slot_clients={}, document=ACTIONS_ANSWER))
