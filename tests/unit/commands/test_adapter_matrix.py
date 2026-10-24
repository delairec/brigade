import argparse
import functools
import tempfile
import unittest
from pathlib import Path

from brigade.commands.adapter_matrix import COMMAND, adapter_matrix
from brigade.errors import ToolFailure, UsageError
from brigade.system.resolve_plugin import PluginSources, resolve_plugin
from brigade.system.run_process import ProcessRecord, ProcessRequest
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

BARE_PROBE = (
    '{"schema_version": 1, "client": "bare", "version_argv": null, "operations": ["probe"], "features": [],'
    ' "models": {}}'
)


def _time_out(request: ProcessRequest):
    raise ToolFailure(f"{' '.join(request.argv)} timed out after 30 s")


def _answer_the_bare_probe(request: ProcessRequest) -> ProcessRecord:
    return ProcessRecord(argv=request.argv, cwd=request.cwd, exit_code=0, stdout=BARE_PROBE, stderr="", duration_ms=0)


class AdapterMatrixOfAnAdapterAnsweringOnlyTheProbeTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        root = Path(self.root.name)
        search_directory = root / "bin"
        search_directory.mkdir()
        executable = search_directory / "brigade-client-bare"
        executable.write_text("#!/bin/sh\n")
        executable.chmod(0o755)
        sources = PluginSources(executable_search_path=str(search_directory), run_process=_answer_the_bare_probe)
        self.runtime = create_test_runtime(
            create_test_paths(root, executable_search_path=str(search_directory)),
            run_process=_answer_the_bare_probe,
            resolve_plugin=functools.partial(resolve_plugin, sources=sources),
        )

    def test_should_grade_absent_an_operation_with_no_fallback(self):
        # Arrange
        no_option = argparse.Namespace()

        # Act
        document = adapter_matrix(no_option, self.runtime)

        # Assert
        self.assertEqual(
            document["adapters"][0],
            {
                "name": "bare",
                "audience": "supported_client",
                "capabilities": {
                    "launch": "absent",
                    "result": "absent",
                    "resume": "fallback",
                    "transcripts": "fallback",
                    "actions": "fallback",
                    "step_count": "fallback",
                    "tool_grants": "fallback",
                    "reset_hour": "fallback",
                    "graceful_stop": "fallback",
                },
                "error": None,
            },
        )


class AdapterMatrixWhenAProbeTimesOutTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        root = Path(self.root.name)
        search_directory = root / "bin"
        search_directory.mkdir()
        self.executable = search_directory / "brigade-client-slow"
        self.executable.write_text("#!/bin/sh\n")
        self.executable.chmod(0o755)
        sources = PluginSources(executable_search_path=str(search_directory), run_process=_time_out)
        self.runtime = create_test_runtime(
            create_test_paths(root, executable_search_path=str(search_directory)),
            run_process=_time_out,
            resolve_plugin=functools.partial(resolve_plugin, sources=sources),
        )

    def tearDown(self):
        self.root.cleanup()

    def test_should_name_the_timeout_in_the_row_of_the_adapter(self):
        # Arrange
        no_option = argparse.Namespace()

        # Act
        document = adapter_matrix(no_option, self.runtime)

        # Assert
        self.assertEqual(
            document["adapters"][1],
            {
                "name": "slow",
                "audience": "supported_client",
                "capabilities": None,
                "error": f"{self.executable} probe timed out after 30 s",
            },
        )


def _answer_a_probe_lacking_its_version_argv(request: ProcessRequest) -> ProcessRecord:
    return ProcessRecord(
        argv=request.argv,
        cwd=request.cwd,
        exit_code=0,
        stdout='{"schema_version": 1, "client": "broken", "operations": ["probe"], "features": [], "models": {}}',
        stderr="",
        duration_ms=0,
    )


class AdapterMatrixWhenAProbeAnswersOffItsShapeTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        root = Path(self.root.name)
        search_directory = root / "bin"
        search_directory.mkdir()
        executable = search_directory / "brigade-client-broken"
        executable.write_text("#!/bin/sh\n")
        executable.chmod(0o755)
        sources = PluginSources(
            executable_search_path=str(search_directory), run_process=_answer_a_probe_lacking_its_version_argv
        )
        self.runtime = create_test_runtime(
            create_test_paths(root, executable_search_path=str(search_directory)),
            run_process=_answer_a_probe_lacking_its_version_argv,
            resolve_plugin=functools.partial(resolve_plugin, sources=sources),
        )

    def test_should_name_the_key_the_answer_lacks_in_the_row_of_the_adapter(self):
        # Arrange
        no_option = argparse.Namespace()

        # Act
        document = adapter_matrix(no_option, self.runtime)

        # Assert
        self.assertEqual(
            document["adapters"][0],
            {
                "name": "broken",
                "audience": "supported_client",
                "capabilities": None,
                "error": "client adapter broken answered probe: lacks the key version_argv",
            },
        )


class AdapterMatrixOfAnAdapterWithSettingsInTheConfigurationTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        root = Path(self.root.name)
        search_directory = root / "bin"
        search_directory.mkdir()
        paths = create_test_paths(root, executable_search_path=str(search_directory))
        paths.configuration_file.parent.mkdir(parents=True)
        paths.configuration_file.write_text('[clients.fake]\nfeatures = "step_count"\n')
        sources = PluginSources(executable_search_path=str(search_directory), run_process=_answer_the_bare_probe)
        self.runtime = create_test_runtime(
            paths, run_process=_answer_the_bare_probe, resolve_plugin=functools.partial(resolve_plugin, sources=sources)
        )

    def test_should_probe_the_adapter_with_its_settings(self):
        # Arrange
        no_option = argparse.Namespace()

        # Act
        document = adapter_matrix(no_option, self.runtime)

        # Assert
        self.assertEqual(
            document["adapters"][1],
            {
                "name": "fake",
                "audience": "test_suite",
                "capabilities": {
                    "launch": "full",
                    "result": "full",
                    "resume": "fallback",
                    "transcripts": "fallback",
                    "actions": "fallback",
                    "step_count": "full",
                    "tool_grants": "fallback",
                    "reset_hour": "fallback",
                    "graceful_stop": "fallback",
                },
                "error": None,
            },
        )


MATRIX = {
    "schema_version": 1,
    "adapters": [
        {
            "name": "claude-code",
            "audience": "supported_client",
            "capabilities": {
                "launch": "full",
                "result": "full",
                "resume": "full",
                "transcripts": "full",
                "actions": "full",
                "step_count": "full",
                "tool_grants": "full",
                "reset_hour": "full",
                "graceful_stop": "fallback",
            },
            "error": None,
        },
        {"name": "broken", "audience": "test_suite", "capabilities": None, "error": "no JSON | answer"},
    ],
    "fallbacks": {
        "resume": "a fresh launch from the progress file",
        "graceful_stop": "the hard cut at the wall-time limit",
    },
}


class AdapterMatrixTextTest(unittest.TestCase):
    def test_should_print_the_grades_of_each_adapter_its_error_and_the_fallbacks(self):
        # Act
        text = COMMAND.render_text(MATRIX)

        # Assert
        self.assertEqual(
            text,
            "adapter      audience          launch  result  resume  transcripts  actions  step count  tool grants"
            "  reset hour  graceful stop\n"
            "claude-code  supported client  full    full    full    full         full     full        full       "
            "  full        fallback\n"
            "broken       test suite        error: no JSON | answer\n"
            "\n"
            "fallbacks\n"
            "  no resume         a fresh launch from the progress file\n"
            "  no graceful stop  the hard cut at the wall-time limit",
        )


class AdapterMatrixMarkdownTest(unittest.TestCase):
    def test_should_print_one_table_per_audience_with_the_error_cell_escaped(self):
        # Act
        markdown = COMMAND.render_markdown(MATRIX)

        # Assert
        self.assertEqual(
            markdown,
            "| Supported client | Launch | Result | Resume | Transcripts | Actions | Step count | Tool grants"
            " | Reset hour | Graceful stop |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
            "| claude-code | full | full | full | full | full | full | full | full | fallback |\n"
            "\n"
            "| Test-suite adapter | Launch | Result | Resume | Transcripts | Actions | Step count | Tool grants"
            " | Reset hour | Graceful stop |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
            "| broken | error: no JSON \\| answer |  |  |  |  |  |  |  |  |\n"
            "\n"
            "Fallbacks:\n"
            "\n"
            "- no resume: a fresh launch from the progress file\n"
            "- no graceful stop: the hard cut at the wall-time limit",
        )


class AdapterMatrixRequestTest(unittest.TestCase):
    def test_should_refuse_markdown_and_json_together(self):
        # Arrange
        options = argparse.Namespace(markdown=True, json=True)

        # Act
        with self.assertRaises(UsageError) as refusal:
            COMMAND.read_request(options)

        # Assert
        self.assertEqual(str(refusal.exception), "--markdown and --json exclude each other")

    def test_should_take_markdown_alone(self):
        # Arrange
        options = argparse.Namespace(markdown=True, json=False)

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertEqual(request, argparse.Namespace(markdown=True, json=False))


class AdapterMatrixExitCodeTest(unittest.TestCase):
    def test_should_exit_1_when_an_adapter_failed_its_probe_and_0_otherwise(self):
        # Arrange
        rows = [("broken", "no JSON", 1), ("bare", None, 0)]
        for name, error, expected in rows:
            with self.subTest(error=error):
                document = {"adapters": [{"name": name, "audience": "test_suite", "error": error}]}

                # Act
                exit_code = COMMAND.decide_exit_code(document)

                # Assert
                self.assertEqual(exit_code, expected)
