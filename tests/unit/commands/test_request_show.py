import os
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.commands.request_show import COMMAND
from brigade.errors import BrigadeError
from brigade.runs.record_run_pid import record_run_pid
from tests.unit.commands.command_runtime import create_corpus_double, write_operational_corpus
from tests.unit.commands.run_directories import create_planner_record, create_run_result, write_run

PLANNED_REQUEST = (
    ("PROJECT", "@PROJECT.shop"),
    ("TEXT", "empty the cart"),
    ("CREATED_AT", "2026-10-13T14:00:00Z"),
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
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

PLANNER_RUN = "20261013T140000Z-a10001"
NO_RESULT = None


class RequestShowTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(self.root)
        self.runtime = create_test_runtime(
            create_test_paths(self.root),
            run_process=create_corpus_double({"REQUEST": {"shop_r1": PLANNED_REQUEST, "shop_r2": PLANNING_REQUEST}}),
        )
        self.state_root = self.root / "state"

    def test_should_describe_the_request_its_plan_and_its_pull_request(self):
        # Act
        document = COMMAND.run(Namespace(request="shop_r1"), self.runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "request": "shop_r1",
                "project": "shop",
                "text": "empty the cart",
                "status": "planned",
                "milestone": "M4",
                "pr": 42,
                "created_at": "2026-10-13T14:00:00Z",
                "planner": None,
            },
        )

    def test_should_say_that_the_planner_run_of_a_planning_request_is_live(self):
        # Arrange
        run_directory = write_run(self.state_root, create_planner_record(PLANNER_RUN, "shop_r2"), NO_RESULT)
        record_run_pid(run_directory, os.getpid())

        # Act
        document = COMMAND.run(Namespace(request="shop_r2"), self.runtime)

        # Assert
        self.assertEqual(document["planner"], {"run": PLANNER_RUN, "state": "live"})

    def test_should_say_that_the_planner_run_of_a_planning_request_is_dead(self):
        # Arrange
        write_run(self.state_root, create_planner_record(PLANNER_RUN, "shop_r2"), NO_RESULT)

        # Act
        document = COMMAND.run(Namespace(request="shop_r2"), self.runtime)

        # Assert
        self.assertEqual(document["planner"], {"run": PLANNER_RUN, "state": "dead"})

    def test_should_say_that_the_planner_run_of_a_planning_request_ended_blocked(self):
        # Arrange
        blocked = create_run_result(PLANNER_RUN, "blocked", "2026-10-13T14:20:00Z")
        write_run(self.state_root, create_planner_record(PLANNER_RUN, "shop_r2"), blocked)

        # Act
        document = COMMAND.run(Namespace(request="shop_r2"), self.runtime)

        # Assert
        self.assertEqual(document["planner"], {"run": PLANNER_RUN, "state": "blocked"})

    def test_should_refuse_a_request_the_operational_corpus_does_not_define(self):
        # Act
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(Namespace(request="shop_r9"), self.runtime)

        # Assert
        self.assertEqual(str(raised.exception), "@REQUEST.shop_r9 is not defined in the operational corpus")


class RequestShowTextTest(unittest.TestCase):
    def test_should_print_the_request_its_text_and_its_plan(self):
        # Arrange
        document = {
            "schema_version": 1,
            "request": "shop_r2",
            "project": "shop",
            "text": "show the total of the cart",
            "status": "planning",
            "milestone": None,
            "pr": None,
            "created_at": "2026-10-13T14:00:00Z",
            "planner": None,
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "@REQUEST.shop_r2 of @PROJECT.shop  planning\n"
            "show the total of the cart\n"
            "milestone   -\n"
            "pr          -\n"
            "created at  2026-10-13T14:00:00Z\n"
            "planner     -",
        )

    def test_should_print_the_state_of_the_planner_run_and_its_id(self):
        # Arrange
        document = {
            "schema_version": 1,
            "request": "shop_r2",
            "project": "shop",
            "text": "show the total of the cart",
            "status": "planning",
            "milestone": None,
            "pr": None,
            "created_at": "2026-10-13T14:00:00Z",
            "planner": {"run": "20261013T140000Z-a10001", "state": "dead"},
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "@REQUEST.shop_r2 of @PROJECT.shop  planning\n"
            "show the total of the cart\n"
            "milestone   -\n"
            "pr          -\n"
            "created at  2026-10-13T14:00:00Z\n"
            "planner     dead, run 20261013T140000Z-a10001",
        )


class RequestShowExitCodeTest(unittest.TestCase):
    def test_should_succeed(self):
        # Act
        exit_code = COMMAND.decide_exit_code({"schema_version": 1})

        # Assert
        self.assertEqual(exit_code, 0)


class RequestShowRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_the_request(self):
        # Arrange
        options = Namespace(request="shop_r1")

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)
