import argparse
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from brigade.commands.adapter_launch_argv import COMMAND, adapter_launch_argv
from brigade.system.ask_configured_client import ConfiguredClientAnswer
from tests.unit.commands.create_command_runtime import create_command_runtime
from tests.unit.commands.create_plugin_resolver import ScriptedClient, create_plugin_resolver

LAUNCH_REQUEST = (
    '{"schema_version": 1, "worktree": "/srv/b42", "brief": "Deliver the task B42.", "session_id": "s1", "stop_at": null,'
    ' "progress_file": "/state/brigade/runs/r1/progress.md", "role": {"name": "builder", "package": "AGENT builder",'
    ' "package_file": "/state/brigade/runs/r1/role.md", "capabilities": ["read"], "reasoning": "standard",'
    ' "budget": 75}}'
)
LAUNCH_ANSWER = {
    "schema_version": 1,
    "argv": ["scripted", "--session", "s1"],
    "environment": {},
    "stdin": None,
    "session_id": "s1",
}


class AdapterLaunchArgvTextTest(unittest.TestCase):
    def test_should_print_the_answer_of_the_adapter_as_indented_json(self):
        # Arrange
        document = {"schema_version": 1, "client": "fake"}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, '{\n  "schema_version": 1,\n  "client": "fake"\n}')


class AdapterLaunchArgvRequestTest(unittest.TestCase):
    def test_should_read_the_request_on_stdin(self):
        # Arrange
        no_option = argparse.Namespace()

        # Act
        with mock.patch("sys.stdin", io.StringIO(LAUNCH_REQUEST)):
            request = COMMAND.read_request(no_option)

        # Assert
        self.assertEqual(request, LAUNCH_REQUEST)


class AdapterLaunchArgvExitCodeTest(unittest.TestCase):
    def test_should_exit_0_once_the_adapter_answered(self):
        # Act
        exit_code = COMMAND.decide_exit_code(LAUNCH_ANSWER)

        # Assert
        self.assertEqual(exit_code, 0)


class AdapterLaunchArgvOfTheConfiguredClientTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        client = ScriptedClient({"launch-argv": LAUNCH_ANSWER})
        self.runtime = create_command_runtime(
            Path(self.root.name), resolve_plugin=create_plugin_resolver({("client", "scripted"): client})
        )
        self.runtime.paths.config_root.mkdir(parents=True)
        self.runtime.paths.configuration_file.write_text('client = "scripted"\n[slot_clients]\nreview = "other"\n')

    def test_should_answer_the_launch_of_the_configured_client_and_the_slot_bound_elsewhere(self):
        # Act
        answer = adapter_launch_argv(LAUNCH_REQUEST, self.runtime)

        # Assert
        self.assertEqual(
            answer,
            ConfiguredClientAnswer(client="scripted", slot_clients={"review": "other"}, document=LAUNCH_ANSWER),
        )
