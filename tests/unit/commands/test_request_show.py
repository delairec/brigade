import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from brigade.commands.request_show import COMMAND
from brigade.errors import BrigadeError
from tests.unit.commands.command_runtime import create_corpus_double, create_runtime, write_operational_corpus

PLANNED_REQUEST = (
    ("PROJECT", "@PROJECT.shop"),
    ("TEXT", "empty the cart"),
    ("CREATED_AT", "2026-10-13T14:00:00Z"),
    ("STATUS", "planned"),
    ("MILESTONE", "M4"),
    ("PR", "42"),
)


class RequestShowTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(self.root)
        self.runtime = create_runtime(
            self.root, run_process=create_corpus_double({"REQUEST": {"shop_r1": PLANNED_REQUEST}})
        )

    def test_should_describe_the_request_its_plan_and_its_pull_request(self):
        # Act
        document = COMMAND.run(SimpleNamespace(request="shop_r1"), self.runtime)

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
            },
        )

    def test_should_refuse_a_request_the_operational_corpus_does_not_define(self):
        # Act
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(SimpleNamespace(request="shop_r9"), self.runtime)

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
            "created at  2026-10-13T14:00:00Z",
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
        options = SimpleNamespace(request="shop_r1")

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)
