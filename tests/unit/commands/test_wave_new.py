import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from brigade.commands.wave_new import COMMAND
from brigade.errors import BrigadeError
from tests.unit.commands.command_runtime import (
    create_corpus_double,
    create_machine_double,
    create_runtime,
    write_operational_corpus,
)
from tests.unit.commands.run_doubles import (
    CLIENT_AND_DOCUMENT_CONFIGURATION,
    CLOCK_PROBE,
    STEP_COUNTING_PROBE,
    create_plugin_resolution,
    spawn_as_this_process,
)

CORPUS_CHANGE_OUTPUTS = {("awawa", "fmt"): "", ("awawa", "lint"): "", ("git", "add"): "", ("git", "diff"): ""}
PAUSED_PROJECT = (("PATH", "/home/user/tidepool"), ("STATUS", "paused"))


class WaveNewTextTest(unittest.TestCase):
    def test_should_name_the_request_and_how_to_follow_its_planning(self):
        # Act
        text = COMMAND.render_text({"schema_version": 1, "request": "tidepool_1", "run": "20261019T090000Z-a1b2c3"})

        # Assert
        self.assertEqual(
            text,
            "@REQUEST.tidepool_1 planning, run 20261019T090000Z-a1b2c3\n"
            "brigade runs show 20261019T090000Z-a1b2c3 --log",
        )


class WaveNewDiagnosticsTest(unittest.TestCase):
    def test_should_pass_on_the_warnings_of_the_planning_run(self):
        # Arrange
        rows = [
            ("no warning", {}, []),
            ("a warning", {"warnings": ["double counts no steps"]}, ["double counts no steps"]),
        ]
        for case, warnings, expected_diagnostics in rows:
            with self.subTest(case=case):
                # Act
                diagnostics = COMMAND.describe_diagnostics({"schema_version": 1, **warnings})

                # Assert
                self.assertEqual(diagnostics, expected_diagnostics)


class WaveNewExitCodeTest(unittest.TestCase):
    def test_should_succeed(self):
        # Act
        exit_code = COMMAND.decide_exit_code({"schema_version": 1})

        # Assert
        self.assertEqual(exit_code, 0)


class WaveNewRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_the_request(self):
        # Arrange
        options = SimpleNamespace(project="tidepool", text="add the tides")

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)


class WaveNewOfAProjectTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        write_operational_corpus(self.root)
        (self.root / "config" / "config.toml").write_text(CLIENT_AND_DOCUMENT_CONFIGURATION, encoding="utf-8")
        (self.root / "tidepool").mkdir()
        self.entities = {"PROJECT": {"tidepool": (("PATH", str(self.root / "tidepool")), ("STATUS", "active"))}}

    def test_should_record_the_request_and_launch_its_planning(self):
        # Arrange
        runtime = create_runtime(
            self.root,
            run_process=create_machine_double(self.entities, CORPUS_CHANGE_OUTPUTS),
            spawn_process=spawn_as_this_process,
            resolve_plugin=create_plugin_resolution(STEP_COUNTING_PROBE),
        )

        # Act
        document = COMMAND.run(SimpleNamespace(project="tidepool", text="add the tides"), runtime)

        # Assert
        [run_directory] = (self.root / "state" / "runs").iterdir()
        self.assertEqual(document, {"schema_version": 1, "request": "tidepool_1", "run": run_directory.name})

    def test_should_pass_on_the_warning_of_a_client_counting_no_steps(self):
        # Arrange
        runtime = create_runtime(
            self.root,
            run_process=create_machine_double(self.entities, CORPUS_CHANGE_OUTPUTS),
            spawn_process=spawn_as_this_process,
            resolve_plugin=create_plugin_resolution(CLOCK_PROBE),
        )

        # Act
        document = COMMAND.run(SimpleNamespace(project="tidepool", text="add the tides"), runtime)

        # Assert
        self.assertEqual(
            document["warnings"],
            [
                "double counts no steps: the budget of 30 steps is held on the clock and the run cut at its limit of 1140 s"
            ],
        )

    def test_should_refuse_a_paused_project(self):
        # Arrange
        runtime = create_runtime(self.root, run_process=create_corpus_double({"PROJECT": {"tidepool": PAUSED_PROJECT}}))

        # Act
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(SimpleNamespace(project="tidepool", text="add the tides"), runtime)

        # Assert
        self.assertEqual(str(raised.exception), "@PROJECT.tidepool is paused")
