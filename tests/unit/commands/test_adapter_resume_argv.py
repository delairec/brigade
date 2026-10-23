import argparse
import io
import tempfile
import unittest
from pathlib import Path

from brigade.commands.adapter_resume_argv import COMMAND, adapter_resume_argv
from brigade.system.ask_configured_client import ConfiguredClientAnswer
from tests.unit.commands.command_runtime import create_runtime
from tests.unit.commands.create_plugin_resolver import ScriptedClient, create_plugin_resolver

RESUME_REQUEST = (
    '{"schema_version": 1, "worktree": "/srv/b42", "brief": "Carry on.", "session_id": "s1", "stop_at": null,'
    ' "progress_file": "/state/brigade/runs/r1/progress.md", "role": {"name": "builder", "package": "AGENT builder",'
    ' "package_file": "/state/brigade/runs/r1/role.md", "capabilities": ["read"], "reasoning": "standard",'
    ' "budget": 75}}'
)
RESUME_ANSWER = {
    "schema_version": 1,
    "argv": ["scripted", "--resume", "s1"],
    "environment": {},
    "stdin": None,
    "session_id": "s1",
}


class AdapterResumeArgvTextTest(unittest.TestCase):
    def test_should_print_the_answer_of_the_adapter_as_indented_json(self):
        # Arrange
        document = {"schema_version": 1, "client": "fake"}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, '{\n  "schema_version": 1,\n  "client": "fake"\n}')


class AdapterResumeArgvRequestTest(unittest.TestCase):
    def test_should_read_the_request_on_stdin(self):
        # Arrange
        options = argparse.Namespace(standard_input=io.StringIO(RESUME_REQUEST))

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertEqual(request, RESUME_REQUEST)


class AdapterResumeArgvExitCodeTest(unittest.TestCase):
    def test_should_exit_0_once_the_adapter_answered(self):
        # Act
        exit_code = COMMAND.decide_exit_code(RESUME_ANSWER)

        # Assert
        self.assertEqual(exit_code, 0)


class AdapterResumeArgvOfTheConfiguredClientTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        client = ScriptedClient({"resume-argv": RESUME_ANSWER})
        self.runtime = create_runtime(
            Path(self.root.name), resolve_plugin=create_plugin_resolver({("client", "scripted"): client})
        )
        self.runtime.paths.config_root.mkdir(parents=True)
        self.runtime.paths.configuration_file.write_text('client = "scripted"\n')

    def test_should_answer_the_resumption_of_the_configured_client(self):
        # Act
        answer = adapter_resume_argv(RESUME_REQUEST, self.runtime)

        # Assert
        self.assertEqual(answer, ConfiguredClientAnswer(client="scripted", slot_clients={}, document=RESUME_ANSWER))
