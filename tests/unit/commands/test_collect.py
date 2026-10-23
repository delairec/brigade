import argparse
import contextlib
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

from brigade.commands.collect import COMMAND, collect
from tests.unit.commands.create_plugin_resolver import create_plugin_resolver

NOTES_DOCUMENT = (
    '{"schema_version": 1, "collector": "notes", "collected_at": "2026-10-19T09:00:00Z",'
    ' "summary": {"open": 3}, "items": []}'
)
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime


class ScriptedCollectorDouble:
    name = "notes"
    source = "project"
    command = ("/srv/app/.brigade/collectors/notes",)

    def __init__(self):
        self.environments = []

    def collect(self, environment: dict, runtime, equipment):
        self.environments.append(environment)
        return SimpleNamespace(exit_code=0, stdout=NOTES_DOCUMENT, stderr="", duration_ms=40)


class CollectTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        root = Path(self.root.name).resolve()
        self.project = root / "app"
        self.project.mkdir()
        self.enterContext(contextlib.chdir(self.project))
        self.collector = ScriptedCollectorDouble()
        self.runtime = create_test_runtime(
            create_test_paths(root),
            resolve_plugin=create_plugin_resolver(
                {("collector", "notes"): self.collector, ("forge", "github"): object()}
            ),
        )

    def test_should_give_the_summary_and_the_place_of_the_document_collected(self):
        # Arrange
        request = argparse.Namespace(name="notes", since=None, refresh=False, extra_arguments=[])

        # Act
        document = collect(request, self.runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "collector": "notes",
                "source": "project",
                "cached": False,
                "summary": {"open": 3},
                "document": str(self.runtime.paths.state_root / "collect" / "notes" / "document.json"),
            },
        )

    def test_should_hand_the_collector_the_project_the_day_since_names_and_the_parameters(self):
        # Arrange
        rows = [
            (None, "1970-01-01"),
            (timedelta(days=2), "2026-10-17"),
            (date(2026, 10, 1), "2026-10-01"),
        ]
        for since, day in rows:
            with self.subTest(since=since):
                request = argparse.Namespace(name="notes", since=since, refresh=True, extra_arguments=["kind=todo"])

                # Act
                collect(request, self.runtime)

                # Assert
                self.assertEqual(
                    self.collector.environments[-1],
                    {
                        "BRIGADE_PROJECT_PATH": str(self.project),
                        "BRIGADE_SINCE": day,
                        "BRIGADE_PARAMS": '{"kind": "todo"}',
                    },
                )


class CollectExtraArgumentTest(unittest.TestCase):
    def test_should_accept_a_key_value_pair_and_nothing_else(self):
        # Arrange
        rows = [("kind=todo", True), ("--kind=todo", False), ("todo", False)]
        for argument, expected in rows:
            with self.subTest(argument=argument):
                # Act
                accepted = COMMAND.accept_extra_argument(argument)

                # Assert
                self.assertEqual(accepted, expected)


class CollectRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_they_are(self):
        # Arrange
        options = argparse.Namespace(name="notes", refresh=False)

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertEqual(request, argparse.Namespace(name="notes", refresh=False))


class CollectExitCodeTest(unittest.TestCase):
    def test_should_exit_0_once_the_document_is_collected(self):
        # Arrange
        document = {"collector": "notes", "cached": True}

        # Act
        exit_code = COMMAND.decide_exit_code(document)

        # Assert
        self.assertEqual(exit_code, 0)


class CollectTextTest(unittest.TestCase):
    def test_should_print_the_origin_the_summary_and_the_document(self):
        # Arrange
        document = {
            "collector": "notes",
            "cached": True,
            "summary": {"open": 3, "oldest": "2026-10-01"},
            "document": "/cache/notes/document.json",
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "notes from cache\nopen      3\noldest    2026-10-01\ndocument  /cache/notes/document.json",
        )

    def test_should_say_collected_for_a_document_collected_afresh(self):
        # Arrange
        document = {"collector": "notes", "cached": False, "summary": {}, "document": "/state/notes/document.json"}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, "notes collected\ndocument  /state/notes/document.json")
