import argparse
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from brigade.commands.adapter_transcripts import COMMAND, adapter_transcripts
from brigade.system.ask_configured_client import ConfiguredClientAnswer
from tests.unit.commands.command_runtime import create_runtime
from tests.unit.commands.create_plugin_resolver import ScriptedClient, create_plugin_resolver

TRANSCRIPTS_REQUEST = '{"schema_version": 1, "session_id": "s1", "worktree": "/srv/b42"}'
TRANSCRIPTS_ANSWER = {
    "schema_version": 1,
    "messages": [
        {
            "role": "user",
            "timestamp": "2026-10-06T10:00:00.000Z",
            "content": "Deliver the task B42.",
            "tool_calls": 0,
            "id": None,
            "usage": None,
        }
    ],
    "subagents": [],
}


class AdapterTranscriptsTextTest(unittest.TestCase):
    def test_should_print_the_answer_of_the_adapter_as_indented_json(self):
        # Arrange
        document = {"schema_version": 1, "subagents": []}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, '{\n  "schema_version": 1,\n  "subagents": []\n}')


class AdapterTranscriptsRequestTest(unittest.TestCase):
    def test_should_read_the_request_on_stdin(self):
        # Arrange
        no_option = argparse.Namespace()

        # Act
        with mock.patch("sys.stdin", io.StringIO(TRANSCRIPTS_REQUEST)):
            request = COMMAND.read_request(no_option)

        # Assert
        self.assertEqual(request, TRANSCRIPTS_REQUEST)


class AdapterTranscriptsExitCodeTest(unittest.TestCase):
    def test_should_exit_0_once_the_adapter_answered(self):
        # Act
        exit_code = COMMAND.decide_exit_code(TRANSCRIPTS_ANSWER)

        # Assert
        self.assertEqual(exit_code, 0)


class AdapterTranscriptsOfTheConfiguredClientTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        client = ScriptedClient({"transcripts": TRANSCRIPTS_ANSWER})
        self.runtime = create_runtime(
            Path(self.root.name), resolve_plugin=create_plugin_resolver({("client", "scripted"): client})
        )
        self.runtime.paths.config_root.mkdir(parents=True)
        self.runtime.paths.configuration_file.write_text('client = "scripted"\n')

    def test_should_answer_the_transcripts_of_the_session(self):
        # Act
        answer = adapter_transcripts(TRANSCRIPTS_REQUEST, self.runtime)

        # Assert
        self.assertEqual(
            answer, ConfiguredClientAnswer(client="scripted", slot_clients={}, document=TRANSCRIPTS_ANSWER)
        )
