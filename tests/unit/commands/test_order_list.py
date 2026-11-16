import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.commands.order_list import COMMAND
from tests.unit.commands.command_runtime import create_corpus_double, write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

NIGHTLY_ORDER = (
    ("RECIPE", "usage-report"),
    ("PROJECT", "@PROJECT.oak"),
    ("PARAM", "pull_request=12"),
    ("EVERY", "daily@07:00"),
    ("STATUS", "active"),
)
CLEANUP_ORDER = (("RECIPE", "cleanup"), ("STATUS", "paused"))


class OrderListTextTest(unittest.TestCase):
    def test_should_say_that_no_order_is_recorded(self):
        # Act
        text = COMMAND.render_text({"schema_version": 1, "orders": []})

        # Assert
        self.assertEqual(text, "no order recorded")

    def test_should_print_one_row_per_order_marking_what_is_absent(self):
        # Arrange
        document = {
            "schema_version": 1,
            "orders": [
                {"name": "cleanup", "recipe": "cleanup", "project": None, "every": None, "status": "paused"},
                {
                    "name": "nightly",
                    "recipe": "usage-report",
                    "project": "oak",
                    "every": "daily@07:00",
                    "status": "active",
                },
            ],
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "name     recipe        project  every        status\n"
            "cleanup  cleanup       -        -            paused\n"
            "nightly  usage-report  oak      daily@07:00  active",
        )


class OrderListTest(unittest.TestCase):
    def test_should_list_the_orders_with_their_recipe_project_schedule_and_status(self):
        # Arrange
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        write_operational_corpus(root)
        runtime = create_test_runtime(
            create_test_paths(root),
            run_process=create_corpus_double({"ORDER": {"nightly": NIGHTLY_ORDER, "cleanup": CLEANUP_ORDER}}),
        )

        # Act
        document = COMMAND.run(Namespace(), runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "orders": [
                    {"name": "cleanup", "recipe": "cleanup", "project": None, "every": None, "status": "paused"},
                    {
                        "name": "nightly",
                        "recipe": "usage-report",
                        "project": "oak",
                        "every": "daily@07:00",
                        "status": "active",
                    },
                ],
            },
        )
