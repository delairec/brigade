import argparse
import tempfile
import unittest
from pathlib import Path

from brigade.commands.inbox_dismiss import COMMAND, inbox_dismiss
from brigade.errors import BrigadeError
from brigade.inbox.read_inbox import Signal, read_inbox
from tests.unit.commands.command_runtime import (
    ProcessAnswer,
    ScriptedProcessRunner,
    create_corpus_double,
    write_operational_corpus,
)
from tests.unit.commands.inbox_lines import (
    NOTE_ON_OAK_DISMISSED,
    NOTE_ON_OAK_RECORDED,
    THREAD_DISMISSED,
    THREAD_RECORDED,
)
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import FIXED_NOW, create_test_runtime


class InboxDismissTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.runtime = create_test_runtime(create_test_paths(Path(directory.name)))
        self.signals = self.runtime.paths.state_root / "inbox" / "signals.jsonl"
        self.signals.parent.mkdir(parents=True)
        self.signals.write_text(NOTE_ON_OAK_RECORDED + THREAD_RECORDED + THREAD_DISMISSED, encoding="utf-8")

    def test_should_dismiss_the_signal_the_id_names(self):
        # Arrange
        request = argparse.Namespace(id="a4a5f46")

        # Act
        inbox_dismiss(request, self.runtime)

        # Assert
        self.assertEqual(
            read_inbox(self.runtime.paths.state_root, FIXED_NOW)[0],
            Signal(
                id="a4a5f464d8bb319accf7b46a8bf8e366b35f89e2598d104fce5192ffc52659bc",
                fingerprint="note:474fa40ae4db",
                kind="note",
                project="oak",
                count=1,
                age_s=172800,
                status="dismissed",
                evidence={"text": "fix the flaky test"},
            ),
        )

    def test_should_answer_the_signal_it_dismissed(self):
        # Arrange
        request = argparse.Namespace(id="a4a5f46")

        # Act
        document = inbox_dismiss(request, self.runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "signal": "a4a5f464d8bb319accf7b46a8bf8e366b35f89e2598d104fce5192ffc52659bc",
                "fingerprint": "note:474fa40ae4db",
                "changed": True,
            },
        )

    def test_should_leave_a_signal_already_dismissed_as_it_is(self):
        # Arrange
        request = argparse.Namespace(id="1975")

        # Act
        inbox_dismiss(request, self.runtime)

        # Assert
        self.assertEqual(
            self.signals.read_text(encoding="utf-8"), NOTE_ON_OAK_RECORDED + THREAD_RECORDED + THREAD_DISMISSED
        )


class InboxDismissTextTest(unittest.TestCase):
    def test_should_name_the_signal_it_dismissed(self):
        # Arrange
        rows = [
            ("a signal dismissed now", True, "dismissed a4a5f46 note:474fa40ae4db"),
            ("a signal dismissed earlier", False, "a4a5f46 note:474fa40ae4db is already dismissed"),
        ]
        for case, changed, expected_text in rows:
            with self.subTest(case=case):
                # Act
                text = COMMAND.render_text(
                    {
                        "schema_version": 1,
                        "signal": "a4a5f464d8bb319accf7b46a8bf8e366b35f89e2598d104fce5192ffc52659bc",
                        "fingerprint": "note:474fa40ae4db",
                        "changed": changed,
                    }
                )

                # Assert
                self.assertEqual(text, expected_text)


CORPUS_CHANGE_OUTPUTS = {
    ("awawa", "fmt"): ProcessAnswer(),
    ("awawa", "lint"): ProcessAnswer(),
    ("git", "add"): ProcessAnswer(),
    ("git", "diff"): ProcessAnswer(exit_code=1),
    ("git", "commit"): ProcessAnswer(),
}
NEW_PATTERN_TEXT = (
    "PATTERN CartTimeouts\n"
    '\tTITLE "the cart tests fail on a timeout"\n'
    "\tSTATUS new\n"
    '\tEVIDENCE "note:474fa40ae4db the checkout test timed out"\n'
    "\tACTION wave\n"
    '\tTARGET "shop"\n'
)


class InboxDismissPatternTest(unittest.TestCase):
    def setUp(self):
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(root)
        self.patterns = root / "config" / "patterns.awawa"
        self.patterns.write_text(NEW_PATTERN_TEXT, encoding="utf-8")
        self.signals = root / "state" / "inbox" / "signals.jsonl"
        self.signals.parent.mkdir(parents=True)
        self.signals.write_text(NOTE_ON_OAK_RECORDED + THREAD_RECORDED, encoding="utf-8")
        self.paths = create_test_paths(root)

    def _create_runtime(self, status: str):
        pattern_fields = (
            ("TITLE", "the cart tests fail on a timeout"),
            ("STATUS", status),
            ("EVIDENCE", "note:474fa40ae4db the checkout test timed out"),
            ("ACTION", "wave"),
            ("TARGET", "shop"),
        )
        corpus = {"PATTERN": {"CartTimeouts": pattern_fields}}
        runner = ScriptedProcessRunner(CORPUS_CHANGE_OUTPUTS, fallback=create_corpus_double(corpus))
        return create_test_runtime(self.paths, run_process=runner.run)

    def test_should_set_the_pattern_the_id_names_dismissed(self):
        # Arrange
        runtime = self._create_runtime("new")

        # Act
        document = inbox_dismiss(argparse.Namespace(id="CartTimeouts"), runtime)

        # Assert
        self.assertEqual(document, {"schema_version": 1, "pattern": "CartTimeouts"})
        self.assertEqual(
            self.patterns.read_text(encoding="utf-8"),
            (
                "PATTERN CartTimeouts\n"
                '\tTITLE "the cart tests fail on a timeout"\n'
                "\tSTATUS dismissed\n"
                '\tEVIDENCE "note:474fa40ae4db the checkout test timed out"\n'
                "\tACTION wave\n"
                '\tTARGET "shop"\n'
            ),
        )

    def test_should_dismiss_every_signal_the_evidence_of_the_pattern_cites(self):
        # Arrange
        runtime = self._create_runtime("new")

        # Act
        inbox_dismiss(argparse.Namespace(id="CartTimeouts"), runtime)

        # Assert
        self.assertEqual(
            read_inbox(self.paths.state_root, FIXED_NOW)[0],
            Signal(
                id="a4a5f464d8bb319accf7b46a8bf8e366b35f89e2598d104fce5192ffc52659bc",
                fingerprint="note:474fa40ae4db",
                kind="note",
                project="oak",
                count=1,
                age_s=172800,
                status="dismissed",
                evidence={"text": "fix the flaky test"},
            ),
        )

    def test_should_leave_a_cited_signal_already_dismissed_as_it_is(self):
        # Arrange
        self.signals.write_text(NOTE_ON_OAK_RECORDED + NOTE_ON_OAK_DISMISSED, encoding="utf-8")
        runtime = self._create_runtime("new")

        # Act
        inbox_dismiss(argparse.Namespace(id="CartTimeouts"), runtime)

        # Assert
        self.assertEqual(self.signals.read_text(encoding="utf-8"), NOTE_ON_OAK_RECORDED + NOTE_ON_OAK_DISMISSED)

    def test_should_refuse_a_pattern_that_is_not_new_and_write_nothing(self):
        # Arrange
        runtime = self._create_runtime("ratified")

        # Act
        with self.assertRaises(BrigadeError) as raised:
            inbox_dismiss(argparse.Namespace(id="CartTimeouts"), runtime)

        # Assert
        self.assertEqual(
            str(raised.exception), "@PATTERN.CartTimeouts is ratified: only a new pattern is ratified or dismissed"
        )
        self.assertEqual(self.patterns.read_text(encoding="utf-8"), NEW_PATTERN_TEXT)
        self.assertEqual(self.signals.read_text(encoding="utf-8"), NOTE_ON_OAK_RECORDED + THREAD_RECORDED)

    def test_should_name_the_pattern_it_dismissed(self):
        # Act
        text = COMMAND.render_text({"schema_version": 1, "pattern": "CartTimeouts"})

        # Assert
        self.assertEqual(text, "dismissed @PATTERN.CartTimeouts")
