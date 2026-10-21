import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from brigade.commands.request_list import COMMAND
from tests.unit.commands.command_runtime import create_corpus_double, create_runtime, write_operational_corpus

SHOP_REQUEST = (
    ("PROJECT", "@PROJECT.shop"),
    ("CREATED_AT", "2026-10-13T14:00:00Z"),
    ("STATUS", "planned"),
    ("MILESTONE", "M4"),
    ("PR", "42"),
)
DEPOT_REQUEST = (("PROJECT", "@PROJECT.depot"), ("CREATED_AT", "2026-10-14T08:00:00Z"), ("STATUS", "planning"))
SHOP_ROW = {
    "name": "shop_r1",
    "project": "shop",
    "status": "planned",
    "milestone": "M4",
    "pr": 42,
    "created_at": "2026-10-13T14:00:00Z",
}
DEPOT_ROW = {
    "name": "depot_r1",
    "project": "depot",
    "status": "planning",
    "milestone": None,
    "pr": None,
    "created_at": "2026-10-14T08:00:00Z",
}
EVERY_PROJECT = None


class RequestListTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(self.root)
        requests = {"REQUEST": {"shop_r1": SHOP_REQUEST, "depot_r1": DEPOT_REQUEST}}
        self.runtime = create_runtime(self.root, run_process=create_corpus_double(requests))

    def test_should_list_one_row_per_request(self):
        # Act
        document = COMMAND.run(SimpleNamespace(project=EVERY_PROJECT), self.runtime)

        # Assert
        self.assertEqual(document, {"schema_version": 1, "requests": [DEPOT_ROW, SHOP_ROW]})

    def test_should_narrow_the_rows_to_one_project(self):
        # Act
        document = COMMAND.run(SimpleNamespace(project="depot"), self.runtime)

        # Assert
        self.assertEqual(document, {"schema_version": 1, "requests": [DEPOT_ROW]})

    def test_should_list_no_row_of_a_corpus_holding_no_request(self):
        # Arrange
        runtime = create_runtime(self.root, run_process=create_corpus_double({"REQUEST": {}}))

        # Act
        document = COMMAND.run(SimpleNamespace(project=EVERY_PROJECT), runtime)

        # Assert
        self.assertEqual(document, {"schema_version": 1, "requests": []})


class RequestListTextTest(unittest.TestCase):
    def test_should_print_a_table_with_a_dash_for_what_is_absent(self):
        # Arrange
        document = {"schema_version": 1, "requests": [SHOP_ROW, DEPOT_ROW]}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text.splitlines(),
            [
                "request   project  status    milestone  pr  created at",
                "shop_r1   shop     planned   M4         42  2026-10-13T14:00:00Z",
                "depot_r1  depot    planning  -          -   2026-10-14T08:00:00Z",
            ],
        )


class RequestListExitCodeTest(unittest.TestCase):
    def test_should_succeed(self):
        # Act
        exit_code = COMMAND.decide_exit_code({"schema_version": 1})

        # Assert
        self.assertEqual(exit_code, 0)


class RequestListRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_the_request(self):
        # Arrange
        options = SimpleNamespace(project="shop")

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)
