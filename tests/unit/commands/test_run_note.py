import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.commands.run_note import COMMAND
from brigade.errors import BrigadeError
from tests.unit.commands.run_directories import FIRST_RUN, create_run_record, create_run_result, write_run
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

NOTE_TEXT = "the corpus of main holds two L016 errors"
EARLIER_NOTE = '{"at": "2026-10-19T08:30:00Z", "text": "rebase onto main before the check"}\n'
NO_RESULT = None


class RunNoteTextTest(unittest.TestCase):
    def test_should_render_that_the_note_waits_for_the_next_segment(self):
        # Arrange
        document = {"schema_version": 1, "run": FIRST_RUN, "note": {"at": "2026-10-19T09:00:00Z", "text": NOTE_TEXT}}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            f"noted run {FIRST_RUN}: the note waits for the next segment of the run,"
            " a segment already launched taking no input",
        )


class RunNoteOfARunningRunTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.run_directory = write_run(self.root / "state", create_run_record(FIRST_RUN, None, None), NO_RESULT)
        self.runtime = create_test_runtime(create_test_paths(self.root))

    def test_should_append_the_note_and_its_timestamp_to_the_notes_of_the_run(self):
        # Arrange
        (self.run_directory / "notes.jsonl").write_text(EARLIER_NOTE, encoding="utf-8")

        # Act
        COMMAND.run(Namespace(run=FIRST_RUN, text=NOTE_TEXT), self.runtime)

        # Assert
        self.assertEqual(
            (self.run_directory / "notes.jsonl").read_text(encoding="utf-8"),
            '{"at": "2026-10-19T08:30:00Z", "text": "rebase onto main before the check"}\n'
            '{"at": "2026-10-19T09:00:00Z", "text": "the corpus of main holds two L016 errors"}\n',
        )

    def test_should_answer_the_run_and_the_note_appended(self):
        # Act
        document = COMMAND.run(Namespace(run=FIRST_RUN, text=NOTE_TEXT), self.runtime)

        # Assert
        self.assertEqual(
            document,
            {"schema_version": 1, "run": FIRST_RUN, "note": {"at": "2026-10-19T09:00:00Z", "text": NOTE_TEXT}},
        )

    def test_should_record_the_note_in_the_ledger(self):
        # Act
        COMMAND.run(Namespace(run=FIRST_RUN, text=NOTE_TEXT), self.runtime)

        # Assert
        [ledger_file] = (self.root / "state" / "ledger").glob("*.jsonl")
        self.assertEqual(
            json.loads(ledger_file.read_text(encoding="utf-8")),
            {
                "schema_version": 1,
                "ts": "2026-10-19T09:00:00Z",
                "event": "run.noted",
                "run": FIRST_RUN,
                "text": NOTE_TEXT,
            },
        )


class RunNoteOfARunItCannotNoteTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.runtime = create_test_runtime(create_test_paths(self.root))

    def test_should_refuse_a_run_no_directory_holds(self):
        # Act
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(Namespace(run=FIRST_RUN, text=NOTE_TEXT), self.runtime)

        # Assert
        self.assertEqual(str(raised.exception), f"no run {FIRST_RUN}")

    def test_should_refuse_a_run_whose_result_is_written(self):
        # Arrange
        run_directory = write_run(
            self.root / "state",
            create_run_record(FIRST_RUN, None, None),
            create_run_result(FIRST_RUN, "done", "2026-10-07T09:12:00Z"),
        )

        # Act
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(Namespace(run=FIRST_RUN, text=NOTE_TEXT), self.runtime)

        # Assert
        self.assertEqual(
            str(raised.exception),
            f"run {FIRST_RUN} has already finished on done: no segment of it is left to carry the note",
        )
        self.assertFalse((run_directory / "notes.jsonl").exists())
