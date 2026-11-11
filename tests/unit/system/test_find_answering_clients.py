import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError, ToolFailure, ToolNotFound
from brigade.system.find_answering_clients import find_answering_clients
from tests.unit.client_double import ClientDouble, create_built_in_clients
from tests.unit.commands.command_runtime import ProcessAnswer, ScriptedProcessRunner
from tests.unit.commands.create_plugin_resolver import create_plugin_resolver
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime


class FindAnsweringClientsTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.search_directory = Path(self.root.name) / "bin"
        self.search_directory.mkdir()

    def _create_runtime(self, answers: dict, plugins: dict):
        paths = create_test_paths(Path(self.root.name), executable_search_path=str(self.search_directory))
        return create_test_runtime(
            paths, run_process=ScriptedProcessRunner(answers).run, resolve_plugin=create_plugin_resolver(plugins)
        )

    def test_should_name_the_supported_clients_whose_executable_answers(self):
        # Arrange
        rows = [
            ("claude alone", ProcessAnswer(stdout="2.1.291\n"), ToolNotFound("vibe"), ("claude-code",)),
            ("vibe alone", ToolNotFound("claude"), ProcessAnswer(stdout="1.0.0\n"), ("vibe",)),
            ("both", ProcessAnswer(stdout="2.1.291\n"), ProcessAnswer(stdout="1.0.0\n"), ("claude-code", "vibe")),
            ("none", ToolNotFound("claude"), ToolNotFound("vibe"), ()),
        ]
        for case, claude_answer, vibe_answer, expected in rows:
            with self.subTest(case=case):
                runtime = self._create_runtime(
                    {("claude", "--version"): claude_answer, ("vibe", "--version"): vibe_answer},
                    create_built_in_clients(),
                )

                # Act
                names = find_answering_clients(runtime)

                # Assert
                self.assertEqual(names, expected)

    def test_should_not_count_a_client_whose_version_command_fails(self):
        # Arrange
        runtime = self._create_runtime(
            {("claude", "--version"): ToolFailure("claude --version exited 1"), ("vibe", "--version"): ProcessAnswer()},
            create_built_in_clients(),
        )

        # Act
        names = find_answering_clients(runtime)

        # Assert
        self.assertEqual(names, ("vibe",))

    def test_should_not_count_a_client_whose_probe_is_refused(self):
        # Arrange
        plugins = {
            **create_built_in_clients(),
            ("client", "vibe"): BrigadeError("client adapter vibe answered probe: not a JSON document"),
        }
        runtime = self._create_runtime({("claude", "--version"): ProcessAnswer()}, plugins)

        # Act
        names = find_answering_clients(runtime)

        # Assert
        self.assertEqual(names, ("claude-code",))

    def test_should_count_an_executable_adapter_on_path_that_names_no_client_executable(self):
        # Arrange
        executable_adapter = self.search_directory / "brigade-client-acme"
        executable_adapter.write_text("#!/bin/sh\n")
        executable_adapter.chmod(0o755)
        plugins = {**create_built_in_clients(), ("client", "acme"): ClientDouble("acme", None)}
        runtime = self._create_runtime(
            {("claude", "--version"): ToolNotFound("claude"), ("vibe", "--version"): ToolNotFound("vibe")}, plugins
        )

        # Act
        names = find_answering_clients(runtime)

        # Assert
        self.assertEqual(names, ("acme",))
