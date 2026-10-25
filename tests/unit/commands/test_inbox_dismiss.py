import argparse
import tempfile
import unittest
from pathlib import Path

from brigade.commands.inbox_dismiss import COMMAND, inbox_dismiss
from brigade.inbox.read_inbox import Signal, read_inbox
from tests.unit.commands.inbox_lines import NOTE_ON_OAK_RECORDED, THREAD_DISMISSED, THREAD_RECORDED
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
