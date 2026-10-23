import argparse
import io
import tempfile
import unittest
from pathlib import Path

from brigade.commands.adapter_parse_result import COMMAND, adapter_parse_result
from brigade.system.ask_configured_client import ConfiguredClientAnswer
from tests.unit.commands.command_runtime import create_runtime
from tests.unit.commands.create_plugin_resolver import ScriptedClient, create_plugin_resolver

PARSE_RESULT_REQUEST = '{"schema_version": 1, "exit_code": 0, "stdout": "done", "stderr": ""}'
PARSE_RESULT_ANSWER = {
    "schema_version": 1,
    "outcome": "done",
    "steps": 12,
    "usage": None,
    "session_id": "s1",
    "duration_ms": 1000,
    "cost_usd": None,
    "error_class": None,
    "reset": None,
    "message": None,
}


class AdapterParseResultTextTest(unittest.TestCase):
    def test_should_print_the_answer_of_the_adapter_as_indented_json(self):
        # Arrange
        document = {"schema_version": 1, "outcome": "done"}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, '{\n  "schema_version": 1,\n  "outcome": "done"\n}')


class AdapterParseResultRequestTest(unittest.TestCase):
    def test_should_read_the_request_on_stdin(self):
        # Arrange
        options = argparse.Namespace(standard_input=io.StringIO(PARSE_RESULT_REQUEST))

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertEqual(request, PARSE_RESULT_REQUEST)


class AdapterParseResultExitCodeTest(unittest.TestCase):
    def test_should_exit_0_once_the_adapter_answered(self):
        # Act
        exit_code = COMMAND.decide_exit_code(PARSE_RESULT_ANSWER)

        # Assert
        self.assertEqual(exit_code, 0)


class AdapterParseResultOfTheConfiguredClientTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        client = ScriptedClient({"parse-result": PARSE_RESULT_ANSWER})
        self.runtime = create_runtime(
            Path(self.root.name), resolve_plugin=create_plugin_resolver({("client", "scripted"): client})
        )
        self.runtime.paths.config_root.mkdir(parents=True)
        self.runtime.paths.configuration_file.write_text('client = "scripted"\n')

    def test_should_answer_the_result_the_configured_client_reads(self):
        # Act
        answer = adapter_parse_result(PARSE_RESULT_REQUEST, self.runtime)

        # Assert
        self.assertEqual(
            answer, ConfiguredClientAnswer(client="scripted", slot_clients={}, document=PARSE_RESULT_ANSWER)
        )
