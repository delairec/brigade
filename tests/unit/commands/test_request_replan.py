import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import ANY

from brigade.commands.request_replan import COMMAND
from brigade.errors import BrigadeError
from brigade.runs.record_run_pid import record_run_pid
from tests.unit.commands.command_runtime import create_corpus_double, create_runtime, write_operational_corpus
from tests.unit.commands.run_directories import create_planner_record, create_run_result, write_run
from tests.unit.commands.run_doubles import (
    CLIENT_AND_DOCUMENT_CONFIGURATION,
    STEP_COUNTING_PROBE,
    create_plugin_resolution,
    spawn_as_this_process,
)

PLANNED_REQUEST = (
    ("PROJECT", "@PROJECT.shop"),
    ("TEXT", "empty the cart"),
    ("CREATED_AT", "2026-10-12T09:30:00Z"),
    ("STATUS", "planned"),
    ("MILESTONE", "M4"),
    ("PR", "42"),
)
PLANNING_REQUEST = (
    ("PROJECT", "@PROJECT.shop"),
    ("TEXT", "show the total of the cart"),
    ("CREATED_AT", "2026-10-13T14:00:00Z"),
    ("STATUS", "planning"),
)
PLANNER_RUN = "20261013T140000Z-a10001"
NO_RESULT = None


class RequestReplanTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(self.root)
        (self.root / "config" / "config.toml").write_text(CLIENT_AND_DOCUMENT_CONFIGURATION, encoding="utf-8")
        self.repository = self.root / "shop"
        self.repository.mkdir()
        self.state_root = self.root / "state"

    def _create_runtime(self, project: tuple):
        corpus = {
            "PROJECT": {"shop": project},
            "REQUEST": {"shop_r1": PLANNED_REQUEST, "shop_r2": PLANNING_REQUEST},
        }
        return create_runtime(
            self.root,
            run_process=create_corpus_double(corpus),
            spawn_process=spawn_as_this_process,
            resolve_plugin=create_plugin_resolution(STEP_COUNTING_PROBE),
        )

    def test_should_relaunch_the_planner_of_a_request_whose_planner_run_is_dead(self):
        # Arrange
        write_run(self.state_root, create_planner_record(PLANNER_RUN, "shop_r2"), NO_RESULT)
        runtime = self._create_runtime((("PATH", str(self.repository)),))

        # Act
        document = COMMAND.run(SimpleNamespace(request="shop_r2"), runtime)

        # Assert
        self.assertEqual(document, {"schema_version": 1, "request": "shop_r2", "run": ANY})
        self.assertNotEqual(document["run"], PLANNER_RUN)

    def test_should_relaunch_the_planner_of_a_request_whose_planner_run_ended_blocked(self):
        # Arrange
        blocked = create_run_result(PLANNER_RUN, "blocked", "2026-10-13T14:20:00Z")
        write_run(self.state_root, create_planner_record(PLANNER_RUN, "shop_r2"), blocked)
        runtime = self._create_runtime((("PATH", str(self.repository)),))

        # Act
        document = COMMAND.run(SimpleNamespace(request="shop_r2"), runtime)

        # Assert
        self.assertEqual(document, {"schema_version": 1, "request": "shop_r2", "run": ANY})
        self.assertNotEqual(document["run"], PLANNER_RUN)

    def test_should_launch_the_planner_of_a_request_that_has_no_planner_run(self):
        # Arrange
        runtime = self._create_runtime((("PATH", str(self.repository)),))

        # Act
        document = COMMAND.run(SimpleNamespace(request="shop_r2"), runtime)

        # Assert
        self.assertEqual(document, {"schema_version": 1, "request": "shop_r2", "run": ANY})

    def test_should_refuse_a_request_that_is_not_planning(self):
        # Arrange
        runtime = self._create_runtime((("PATH", str(self.repository)),))

        # Act
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(SimpleNamespace(request="shop_r1"), runtime)

        # Assert
        self.assertEqual(str(raised.exception), "@REQUEST.shop_r1 is planned")

    def test_should_refuse_a_request_whose_planner_run_is_live(self):
        # Arrange
        run_directory = write_run(self.state_root, create_planner_record(PLANNER_RUN, "shop_r2"), NO_RESULT)
        record_run_pid(run_directory, os.getpid())
        runtime = self._create_runtime((("PATH", str(self.repository)),))

        # Act
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(SimpleNamespace(request="shop_r2"), runtime)

        # Assert
        self.assertEqual(str(raised.exception), f"@REQUEST.shop_r2 has its planner run {PLANNER_RUN} live")

    def test_should_refuse_a_request_of_a_paused_project(self):
        # Arrange
        runtime = self._create_runtime((("PATH", str(self.repository)), ("STATUS", "paused")))

        # Act
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(SimpleNamespace(request="shop_r2"), runtime)

        # Assert
        self.assertEqual(str(raised.exception), "@PROJECT.shop is paused")


class RequestReplanTextTest(unittest.TestCase):
    def test_should_name_the_request_its_run_and_the_line_that_follows_it(self):
        # Arrange
        document = {"schema_version": 1, "request": "shop_r2", "run": "20261019T090000Z-a1b2c3"}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "@REQUEST.shop_r2 planning, run 20261019T090000Z-a1b2c3\nbrigade runs show 20261019T090000Z-a1b2c3 --log",
        )


class RequestReplanDiagnosticsTest(unittest.TestCase):
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


class RequestReplanExitCodeTest(unittest.TestCase):
    def test_should_succeed(self):
        # Act
        exit_code = COMMAND.decide_exit_code({"schema_version": 1})

        # Assert
        self.assertEqual(exit_code, 0)


class RequestReplanRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_the_request(self):
        # Arrange
        options = SimpleNamespace(request="shop_r2")

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)


if __name__ == "__main__":
    unittest.main()
