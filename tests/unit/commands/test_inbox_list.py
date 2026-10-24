import argparse
import tempfile
import unittest
from pathlib import Path

from brigade.commands.inbox_list import COMMAND, inbox_list
from tests.unit.commands.inbox_lines import NOTE_ON_OAK_RECORDED, THREAD_DISMISSED, THREAD_RECORDED
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime


class InboxListTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.runtime = create_test_runtime(create_test_paths(Path(directory.name)))
        signals = self.runtime.paths.state_root / "inbox" / "signals.jsonl"
        signals.parent.mkdir(parents=True)
        signals.write_text(NOTE_ON_OAK_RECORDED + THREAD_RECORDED + THREAD_DISMISSED, encoding="utf-8")

    def test_should_list_the_new_signals(self):
        # Arrange
        request = argparse.Namespace(all=False)

        # Act
        document = inbox_list(request, self.runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "signals": [
                    {
                        "id": "a4a5f464d8bb319accf7b46a8bf8e366b35f89e2598d104fce5192ffc52659bc",
                        "fingerprint": "note:474fa40ae4db",
                        "kind": "note",
                        "project": "oak",
                        "count": 1,
                        "age_s": 172800,
                        "status": "new",
                    }
                ],
            },
        )

    def test_should_add_the_dismissed_signals_when_all_are_asked_for(self):
        # Arrange
        request = argparse.Namespace(all=True)

        # Act
        document = inbox_list(request, self.runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "signals": [
                    {
                        "id": "a4a5f464d8bb319accf7b46a8bf8e366b35f89e2598d104fce5192ffc52659bc",
                        "fingerprint": "note:474fa40ae4db",
                        "kind": "note",
                        "project": "oak",
                        "count": 1,
                        "age_s": 172800,
                        "status": "new",
                    },
                    {
                        "id": "19757dd92a2f6de337f3946640b43670c28549c4efa10b5438feb15d3106d66f",
                        "fingerprint": "rt:PRRT_kwDO",
                        "kind": "review_thread",
                        "project": None,
                        "count": 1,
                        "age_s": 3600,
                        "status": "dismissed",
                    },
                ],
            },
        )


class InboxListTextTest(unittest.TestCase):
    def test_should_print_one_row_per_signal(self):
        # Arrange
        document = {
            "schema_version": 1,
            "signals": [
                {
                    "id": "a4a5f464d8bb319accf7b46a8bf8e366b35f89e2598d104fce5192ffc52659bc",
                    "fingerprint": "note:474fa40ae4db",
                    "kind": "note",
                    "project": "oak",
                    "count": 1,
                    "age_s": 172800,
                    "status": "new",
                },
                {
                    "id": "19757dd92a2f6de337f3946640b43670c28549c4efa10b5438feb15d3106d66f",
                    "fingerprint": "rt:PRRT_kwDO",
                    "kind": "review_thread",
                    "project": None,
                    "count": 3,
                    "age_s": 3600,
                    "status": "dismissed",
                },
            ],
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "id       kind           project  count  age  status\n"
            "a4a5f46  note           oak      1      2d   new\n"
            "19757dd  review_thread  -        3      1h   dismissed",
        )

    def test_should_say_the_inbox_holds_no_signal(self):
        # Arrange
        document = {"schema_version": 1, "signals": []}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, "no signal in the inbox")
