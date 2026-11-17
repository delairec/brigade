import argparse
import contextlib
import tempfile
import unittest
from pathlib import Path

from brigade.commands.order_new import COMMAND, order_new
from brigade.errors import BrigadeError
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.recipes.checkout_answers import create_checkout_answers
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner
from tests.unit.registry_answers import create_registry_answers
from tests.value_matchers import PatternMatcher

USAGE_REPORT = (
    'schema_version = 1\nname = "usage-report"\ndescription = "the usage report of a pull request"\n'
    'params = ["pull_request"]\nmax_wall = 30\nsteps = []\n'
)
SHOWN_ORDER = (
    '{"fields": [{"name": "RECIPE", "atoms": ["\\"usage-report\\""]}, {"name": "STATUS", "atoms": ["\\"active\\""]}]}'
)


class OrderNewTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name).resolve()
        write_operational_corpus(root)
        paths = create_test_paths(root)
        (paths.config_root / "recipes").mkdir()
        (paths.config_root / "recipes" / "usage-report.toml").write_text(USAGE_REPORT, encoding="utf-8")
        (root / "shop").mkdir()
        self.enterContext(contextlib.chdir(root / "shop"))
        shop = {"PATH": str(root / "shop"), "MODE": "none"}
        runner = RecordingProcessRunner(
            {
                **create_registry_answers(paths.config_root, {"shop": shop}),
                **create_checkout_answers(root / "shop", root / "shop"),
                ("awawa", "show", "@ORDER.usage_report_20261019T090000Z", "--json", str(paths.config_root)): (
                    ProcessAnswer(stdout=SHOWN_ORDER)
                ),
            }
        )
        self.runtime = create_test_runtime(paths, run_process=runner)
        self.orders = paths.config_root / "orders.awawa"

    def test_should_record_an_order_of_a_project_on_a_schedule_named_after_its_recipe_and_now(self):
        # Arrange
        request = argparse.Namespace(
            recipe="usage-report",
            project="shop",
            every="daily@07:00",
            words=["pull_request=12", "the cost of the last review"],
        )

        # Act
        document = order_new(request, self.runtime)

        # Assert
        self.assertEqual(
            document, {"schema_version": 1, "order": "usage_report_20261019T090000Z", "every": "daily@07:00"}
        )
        self.assertEqual(
            self.orders.read_text(encoding="utf-8"),
            (
                "ORDER usage_report_20261019T090000Z\n"
                '\tRECIPE "usage-report"\n'
                "\tPROJECT @PROJECT.shop\n"
                '\tTEXT "the cost of the last review"\n'
                '\tPARAM "pull_request=12"\n'
                '\tEVERY "daily@07:00"\n'
                "\tSTATUS active\n"
            ),
        )

    def test_should_take_a_word_whose_key_the_recipe_does_not_declare_as_the_text(self):
        # Arrange
        request = argparse.Namespace(recipe="usage-report", project=None, every="daily@07:00", words=["depth=2"])

        # Act
        order_new(request, self.runtime)

        # Assert
        self.assertEqual(
            self.orders.read_text(encoding="utf-8"),
            "ORDER usage_report_20261019T090000Z\n"
            '\tRECIPE "usage-report"\n'
            '\tTEXT "depth=2"\n'
            '\tEVERY "daily@07:00"\n'
            "\tSTATUS active\n",
        )

    def test_should_refuse_a_second_text(self):
        # Arrange
        request = argparse.Namespace(
            recipe="usage-report", project=None, every="daily@07:00", words=["the cost", "the duration"]
        )

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            order_new(request, self.runtime)

        # Assert
        self.assertEqual(
            str(refusal.exception),
            "an order takes one text, and the words the cost and the duration are 2: "
            "quote the text, or write key=value for a param of the recipe usage-report",
        )

    def test_should_refuse_a_recipe_that_does_not_resolve(self):
        # Arrange
        request = argparse.Namespace(recipe="cleanup", project=None, every="daily@07:00", words=[])

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            order_new(request, self.runtime)

        # Assert
        self.assertRegex(str(refusal.exception), "^no recipe cleanup: ")

    def test_should_refuse_a_schedule_the_tick_cannot_read(self):
        # Arrange
        request = argparse.Namespace(recipe="usage-report", project=None, every="sometimes", words=[])

        # Act
        with self.assertRaises(BrigadeError):
            order_new(request, self.runtime)

        # Assert
        self.assertFalse(self.orders.exists())

    def test_should_run_an_order_without_schedule_once(self):
        # Arrange
        request = argparse.Namespace(recipe="usage-report", project=None, every=None, words=[])

        # Act
        document = order_new(request, self.runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "order": "usage_report_20261019T090000Z",
                "every": None,
                "run": PatternMatcher("20261019T090000Z-[0-9a-f]{6}"),
                "state": "done",
            },
        )


class OrderNewTextTest(unittest.TestCase):
    def test_should_say_the_order_recorded_and_its_run_or_its_schedule(self):
        # Arrange
        rows = [
            (
                "an order run once",
                {"schema_version": 1, "order": "cleanup_20261019T090000Z", "every": None, "run": "r1", "state": "done"},
                "@ORDER.cleanup_20261019T090000Z recorded, run r1 done",
            ),
            (
                "an order on a schedule",
                {"schema_version": 1, "order": "cleanup_20261019T090000Z", "every": "daily@07:00"},
                "@ORDER.cleanup_20261019T090000Z recorded, every daily@07:00",
            ),
        ]
        for case, document, expected_text in rows:
            with self.subTest(case=case):
                # Act
                text = COMMAND.render_text(document)

                # Assert
                self.assertEqual(text, expected_text)
