import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import ANY

from brigade.commands.request_new import COMMAND
from brigade.errors import BrigadeError
from tests.unit.commands.command_runtime import (
    ProcessAnswer,
    ScriptedProcessRunner,
    create_corpus_double,
    write_operational_corpus,
)
from tests.unit.commands.run_doubles import (
    CLIENT_AND_DOCUMENT_CONFIGURATION,
    STEP_COUNTING_PROBE,
    create_plugin_resolution,
    spawn_as_this_process,
)
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

CORPUS_CHANGE_OUTPUTS = {
    ("awawa", "fmt"): ProcessAnswer(),
    ("awawa", "lint"): ProcessAnswer(),
    ("git", "add"): ProcessAnswer(),
    ("git", "diff"): ProcessAnswer(exit_code=1),
    ("git", "commit"): ProcessAnswer(),
}


class RequestNewTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(self.root)
        (self.root / "config" / "config.toml").write_text(CLIENT_AND_DOCUMENT_CONFIGURATION, encoding="utf-8")
        self.repository = self.root / "shop"
        self.repository.mkdir()

    def _create_runtime(self, project: tuple, probe: dict):
        corpus = {"PROJECT": {"shop": project}}
        runner = ScriptedProcessRunner(CORPUS_CHANGE_OUTPUTS, fallback=create_corpus_double(corpus))
        return create_test_runtime(
            create_test_paths(self.root),
            run_process=runner.run,
            spawn_process=spawn_as_this_process,
            resolve_plugin=create_plugin_resolution(probe),
        )

    def test_should_record_the_request_and_launch_its_planner_detached(self):
        # Arrange
        runtime = self._create_runtime((("PATH", str(self.repository)),), STEP_COUNTING_PROBE)

        # Act
        document = COMMAND.run(Namespace(project="shop", text="empty the cart"), runtime)

        # Assert
        self.assertEqual(document, {"schema_version": 1, "request": "shop_r1", "run": ANY})

    def test_should_refuse_a_paused_project(self):
        # Arrange
        runtime = self._create_runtime((("PATH", str(self.repository)), ("STATUS", "paused")), STEP_COUNTING_PROBE)

        # Act
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(Namespace(project="shop", text="empty the cart"), runtime)

        # Assert
        self.assertEqual(str(raised.exception), "@PROJECT.shop is paused")


class RequestNewTextTest(unittest.TestCase):
    def test_should_name_the_request_its_run_and_the_line_that_follows_it(self):
        # Arrange
        document = {"schema_version": 1, "request": "shop_r1", "run": "20261019T090000Z-a1b2c3"}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "@REQUEST.shop_r1 planning, run 20261019T090000Z-a1b2c3\nbrigade runs show 20261019T090000Z-a1b2c3 --log",
        )


class RequestNewDiagnosticsTest(unittest.TestCase):
    def test_should_report_the_warnings_of_the_planner_run(self):
        for case, document, expected in [
            ("without warning", {"schema_version": 1}, []),
            (
                "with a warning",
                {"schema_version": 1, "warnings": ["the budget is on the clock"]},
                ["the budget is on the clock"],
            ),
        ]:
            with self.subTest(case=case):
                # Act
                diagnostics = COMMAND.describe_diagnostics(document)

                # Assert
                self.assertEqual(diagnostics, expected)


class RequestNewExitCodeTest(unittest.TestCase):
    def test_should_succeed(self):
        # Act
        exit_code = COMMAND.decide_exit_code({"schema_version": 1})

        # Assert
        self.assertEqual(exit_code, 0)


class RequestNewRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_the_request(self):
        # Arrange
        options = Namespace(project="shop", text="empty the cart")

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)
