import json
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.commands.page import COMMAND
from brigade.errors import BrigadeError
from brigade.system.run_process import ProcessRecord
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.dashboard.addon_child_double import PipedChildDouble

UNDOCUMENTED_EXIT_CODE = 3
ENTRY_POINT = "/srv/brigade/bin/brigade"
EMPTY_INBOX = {"schema_version": 1, "signals": [], "answers": [], "patterns": []}
TWO_WAVES = {
    "schema_version": 1,
    "waves": [
        {"wave": "brigade_w2", "project": "brigade", "started_at": "2026-11-20T10:00:00Z"},
        {"wave": "brigade_w1", "project": "brigade", "started_at": "2026-11-19T10:00:00Z"},
    ],
}
BRIGADE_PROJECT = {"fields": [{"name": "PATH", "atoms": ['"/srv/brigade"']}]}
ONE_PROJECT = {"entities": [{"type": "PROJECT", "name": "brigade"}]}
CORPUS_OF_BRIGADE = {"summary": {"files": 7, "entities": 518}}


class BrigadeDouble:
    def __init__(self, documents: dict[tuple[str, ...], dict]):
        self.documents = documents
        self.asked: list[tuple[str, ...]] = []

    def __call__(self, request) -> ProcessRecord:
        arguments = request.argv[2:] if request.argv[:2] == (sys.executable, ENTRY_POINT) else request.argv
        self.asked.append(arguments)
        document = self.documents.get(arguments)
        if document is None:
            return ProcessRecord(request.argv, request.cwd, UNDOCUMENTED_EXIT_CODE, "", "brigade is down", 0)
        return ProcessRecord(request.argv, request.cwd, 0, json.dumps(document), "", 0)


class PageTextTest(unittest.TestCase):
    def test_should_print_the_page_alone(self):
        # Act
        text = COMMAND.render_text({"schema_version": 1, "page": "home", "html": "<html></html>"})

        # Assert
        self.assertEqual(text, "<html></html>")


class PageTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.paths = create_test_paths(self.root)

    def render(self, page: str, brigade: BrigadeDouble, project: str | None = None, **runtime) -> dict:
        built = create_test_runtime(self.paths, run_process=brigade, **runtime)
        return COMMAND.run(Namespace(page=page, project=project), built)

    def test_should_print_the_page_without_its_script_its_view_filled_from_the_dashboard(self):
        # Arrange
        brigade = BrigadeDouble({("inbox", "list", "--json"): EMPTY_INBOX})

        # Act
        document = self.render("inbox", brigade)

        # Assert
        self.assertNotIn('<script src="/dashboard.js" defer></script>', document["html"])
        self.assertIn("proposed patterns to decide first", document["html"])

    def test_should_offer_no_awawa_tab_on_a_page_of_brigade_itself(self):
        # Arrange
        brigade = BrigadeDouble({("inbox", "list", "--json"): EMPTY_INBOX})

        # Act
        document = self.render("inbox", brigade)

        # Assert
        self.assertNotIn("#awawa/", document["html"])

    def test_should_refuse_a_page_the_dashboard_does_not_have(self):
        # Arrange
        brigade = BrigadeDouble({})

        # Act
        with self.assertRaises(BrigadeError) as raised:
            self.render("foundation", brigade)

        # Assert
        self.assertEqual(
            str(raised.exception),
            "no page foundation; the pages are home, waves, wave, runs, run, ledger, inbox, reports, report, awawa",
        )

    def test_should_refuse_a_page_whose_view_answers_an_error(self):
        # Arrange
        brigade = BrigadeDouble({})

        # Act
        with self.assertRaises(BrigadeError) as raised:
            self.render("inbox", brigade)

        # Assert
        self.assertEqual(
            str(raised.exception), "/views/inbox answered 500: <dl><dt>error</dt><dd>brigade is down</dd></dl>"
        )

    def test_should_show_the_newest_wave_of_the_project_on_the_page_of_a_wave(self):
        # Arrange
        brigade = BrigadeDouble({("wave", "list", "--json"): TWO_WAVES})

        # Act
        with self.assertRaises(BrigadeError) as raised:
            self.render("wave", brigade, project="brigade")

        # Assert
        self.assertEqual(
            str(raised.exception),
            "/views/waves/brigade_w2?project=brigade answered 500: <dl><dt>error</dt><dd>brigade is down</dd></dl>",
        )

    def test_should_refuse_the_page_of_a_wave_when_no_wave_was_ever_started(self):
        # Arrange
        brigade = BrigadeDouble({("wave", "list", "--json"): {"schema_version": 1, "waves": []}})

        # Act
        with self.assertRaises(BrigadeError) as raised:
            self.render("wave", brigade)

        # Assert
        self.assertEqual(str(raised.exception), "the page wave shows one of none: brigade lists none")

    def test_should_refuse_the_awawa_tab_without_a_project(self):
        # Arrange
        brigade = BrigadeDouble({})

        # Act
        with self.assertRaises(BrigadeError) as raised:
            self.render("awawa", brigade)

        # Assert
        self.assertEqual(str(raised.exception), "the page awawa shows the corpus of one project: name it")

    def test_should_ask_the_awawa_addon_for_the_tab_of_the_project(self):
        # Arrange
        self.paths.config_root.mkdir(parents=True)
        self.paths.schema_file.write_text("SCHEMA PROJECT\n")
        brigade = BrigadeDouble(
            {
                ("awawa", "status", "PROJECT", "--json", str(self.paths.config_root)): ONE_PROJECT,
                ("awawa", "show", "@PROJECT.brigade", "--json", str(self.paths.config_root)): BRIGADE_PROJECT,
                ("awawa", "status", "--json", "/srv/brigade"): CORPUS_OF_BRIGADE,
            }
        )
        asked = []

        def answer(message: dict) -> dict:
            asked.append(message)
            return {"error": "no tree"}

        # Act
        with self.assertRaises(BrigadeError):
            self.render(
                "awawa", brigade, project="brigade", start_piped_process=lambda request: PipedChildDouble(answer)
            )

        # Assert
        self.assertEqual(asked[0]["project"], "brigade")
