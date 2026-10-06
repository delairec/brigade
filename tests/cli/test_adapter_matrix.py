import json
import os
import tempfile
import unittest
from pathlib import Path

from tests.cli.temporary_machine import CLONE_ENTRY_POINT, TemporaryMachine

EXECUTABLES = Path(__file__).resolve().parent / "fixtures" / "executables"
SCRIPTED_CLIENT = str(EXECUTABLES / "client-scripted")
BROKEN_CLIENT = str(EXECUTABLES / "client-broken")
MUTE_CLIENT = str(EXECUTABLES / "client-mute")
FAILING_CLIENT = str(EXECUTABLES / "client-failing")

FALLBACKS = {
    "resume": "a fresh launch from the progress file",
    "transcripts": "brigade's own run logs",
    "step_count": "steps null and the run held on the clock alone",
    "tool_grants": "the client's unattended mode and a disposable worktree for a reading slot",
    "reset_hour": "now plus thirty minutes",
}
CLAUDE_CODE_ROW = {
    "name": "claude-code",
    "audience": "supported_client",
    "capabilities": {
        "launch": "full",
        "result": "full",
        "resume": "full",
        "transcripts": "full",
        "step_count": "full",
        "tool_grants": "full",
        "reset_hour": "full",
    },
    "error": None,
}
FAKE_ROW = {
    "name": "fake",
    "audience": "test_suite",
    "capabilities": {
        "launch": "full",
        "result": "full",
        "resume": "fallback",
        "transcripts": "fallback",
        "step_count": "fallback",
        "tool_grants": "fallback",
        "reset_hour": "fallback",
    },
    "error": None,
}
TEXT_LEGEND = (
    "fallbacks\n"
    "  no resume       a fresh launch from the progress file\n"
    "  no transcripts  brigade's own run logs\n"
    "  no step count   steps null and the run held on the clock alone\n"
    "  no tool grants  the client's unattended mode and a disposable worktree for a reading slot\n"
    "  no reset hour   now plus thirty minutes\n"
)


class AdapterMatrixTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        root = Path(self.root.name)
        self.machine = TemporaryMachine(root)
        self.directory_without_adapter = root / "bin"
        self.directory_without_adapter.mkdir()

    def tearDown(self):
        self.root.cleanup()

    def run_matrix(self, *arguments: str, path_directories: tuple = ()):
        search_path = os.pathsep.join([*path_directories, str(self.directory_without_adapter)])
        environment = {**self.machine.describe_environment(), "PATH": search_path}
        return self.machine.run_brigade(CLONE_ENTRY_POINT, "adapter", "matrix", *arguments, environment=environment)


class BrigadeAdapterMatrixOfTheBuiltInAdapters(AdapterMatrixTestCase):
    def test_should_print_a_row_per_adapter_and_a_column_per_capability_then_the_fallbacks(self):
        # Act
        completed = self.run_matrix()

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stdout,
            "adapter      audience          launch  result  resume    transcripts  step count  tool grants  reset hour\n"
            "claude-code  supported client  full    full    full      full         full        full         full\n"
            "fake         test suite        full    full    fallback  fallback     fallback    fallback     fallback\n"
            "\n" + TEXT_LEGEND,
        )

    def test_should_describe_every_adapter_and_the_fallbacks_in_a_versioned_document(self):
        # Act
        completed = self.run_matrix("--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {"schema_version": 1, "adapters": [CLAUDE_CODE_ROW, FAKE_ROW], "fallbacks": FALLBACKS},
        )

    def test_should_print_the_supported_clients_then_the_adapters_of_the_test_suite_as_markdown(self):
        # Act
        completed = self.run_matrix("--markdown")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stdout,
            "| Supported client | Launch | Result | Resume | Transcripts | Step count | Tool grants | Reset hour |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
            "| claude-code | full | full | full | full | full | full | full |\n"
            "\n"
            "| Test-suite adapter | Launch | Result | Resume | Transcripts | Step count | Tool grants | Reset hour |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
            "| fake | full | full | fallback | fallback | fallback | fallback | fallback |\n"
            "\n"
            "Fallbacks:\n"
            "\n"
            "- no resume: a fresh launch from the progress file\n"
            "- no transcripts: brigade's own run logs\n"
            "- no step count: steps null and the run held on the clock alone\n"
            "- no tool grants: the client's unattended mode and a disposable worktree for a reading slot\n"
            "- no reset hour: now plus thirty minutes\n",
        )

    def test_should_probe_each_adapter_with_its_settings_of_config_toml(self):
        # Arrange
        self.machine.write_configuration('[clients.fake]\nfeatures = "step_count"\n')

        # Act
        completed = self.run_matrix("--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout)["adapters"][1],
            {
                "name": "fake",
                "audience": "test_suite",
                "capabilities": {
                    "launch": "full",
                    "result": "full",
                    "resume": "fallback",
                    "transcripts": "fallback",
                    "step_count": "full",
                    "tool_grants": "fallback",
                    "reset_hour": "fallback",
                },
                "error": None,
            },
        )


class BrigadeAdapterMatrixWithAnExecutableAdapterOnPath(AdapterMatrixTestCase):
    def test_should_add_the_executable_as_a_supported_client(self):
        # Act
        completed = self.run_matrix("--json", path_directories=(SCRIPTED_CLIENT,))

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout)["adapters"],
            [
                CLAUDE_CODE_ROW,
                {
                    "name": "scripted",
                    "audience": "supported_client",
                    "capabilities": {
                        "launch": "full",
                        "result": "full",
                        "resume": "fallback",
                        "transcripts": "fallback",
                        "step_count": "fallback",
                        "tool_grants": "fallback",
                        "reset_hour": "fallback",
                    },
                    "error": None,
                },
                FAKE_ROW,
            ],
        )

    def test_should_leave_out_a_file_on_path_that_is_not_executable(self):
        # Arrange
        (self.directory_without_adapter / "brigade-client-inert").write_text("#!/bin/sh\n")

        # Act
        completed = self.run_matrix("--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["adapters"], [CLAUDE_CODE_ROW, FAKE_ROW])


class BrigadeAdapterMatrixWhenAProbeFails(AdapterMatrixTestCase):
    def test_should_name_the_error_of_an_answer_off_the_probe_shape_print_the_other_rows_and_exit_1(self):
        # Act
        completed = self.run_matrix(path_directories=(BROKEN_CLIENT,))

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(
            completed.stdout,
            "adapter      audience          launch  result  resume    transcripts  step count  tool grants  reset hour\n"
            "broken       supported client  error: client adapter broken answered probe: lacks the key version_argv\n"
            "claude-code  supported client  full    full    full      full         full        full         full\n"
            "fake         test suite        full    full    fallback  fallback     fallback    fallback     fallback\n"
            "\n" + TEXT_LEGEND,
        )

    def test_should_name_an_answer_that_is_no_json_document(self):
        # Act
        completed = self.run_matrix("--json", path_directories=(MUTE_CLIENT,))

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(
            json.loads(completed.stdout)["adapters"],
            [
                CLAUDE_CODE_ROW,
                {
                    "name": "mute",
                    "audience": "supported_client",
                    "capabilities": None,
                    "error": "client adapter mute answered probe with no JSON document",
                },
                FAKE_ROW,
            ],
        )

    def test_should_name_the_error_in_the_markdown_row_of_the_adapter(self):
        # Act
        completed = self.run_matrix("--markdown", path_directories=(BROKEN_CLIENT,))

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertIn(
            "| broken | error: client adapter broken answered probe: lacks the key version_argv |  |  |  |  |  |  |\n",
            completed.stdout,
        )

    def test_should_escape_the_cell_separator_of_an_error_in_markdown(self):
        # Act
        completed = self.run_matrix("--markdown", path_directories=(FAILING_CLIENT,))

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertIn(
            f"| failing | error: {FAILING_CLIENT}/brigade-client-failing probe exited 3: no probe \\| no answer"
            " |  |  |  |  |  |  |\n",
            completed.stdout,
        )


class BrigadeAdapterMatrixOptions(AdapterMatrixTestCase):
    def test_should_refuse_markdown_and_json_together(self):
        # Act
        completed = self.run_matrix("--markdown", "--json")

        # Assert
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(completed.stdout, "")
        self.assertEqual(completed.stderr, "brigade adapter matrix: --markdown and --json exclude each other\n")
