import argparse
import tempfile
import unittest
from pathlib import Path

from brigade.commands.inbox_list import COMMAND, inbox_list
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.commands.inbox_lines import NOTE_ON_OAK_RECORDED, THREAD_DISMISSED, THREAD_RECORDED
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.scripted_processes import ScriptedProcesses


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
                "families": [
                    {
                        "by": "signal",
                        "key": "note:474fa40ae4db",
                        "signals": ["a4a5f464d8bb319accf7b46a8bf8e366b35f89e2598d104fce5192ffc52659bc"],
                    }
                ],
                "patterns": [],
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
                "families": [
                    {
                        "by": "signal",
                        "key": "note:474fa40ae4db",
                        "signals": ["a4a5f464d8bb319accf7b46a8bf8e366b35f89e2598d104fce5192ffc52659bc"],
                    },
                    {
                        "by": "signal",
                        "key": "rt:PRRT_kwDO",
                        "signals": ["19757dd92a2f6de337f3946640b43670c28549c4efa10b5438feb15d3106d66f"],
                    },
                ],
                "patterns": [],
            },
        )


class InboxListOfProposedPatternsTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.processes = ScriptedProcesses()
        write_operational_corpus(Path(directory.name))
        self.runtime = create_test_runtime(create_test_paths(Path(directory.name)), run_process=self.processes)
        signals = self.runtime.paths.state_root / "inbox" / "signals.jsonl"
        signals.parent.mkdir(parents=True)
        signals.write_text(NOTE_ON_OAK_RECORDED + THREAD_RECORDED + THREAD_DISMISSED, encoding="utf-8")

    def test_should_carry_each_proposed_pattern_with_its_action_and_the_signals_it_cites(self):
        # Arrange
        self.processes.answer_entities(
            self.runtime.paths.config_root,
            "PATTERN",
            {
                "FlakyTests": (
                    ("TITLE", "the tests are flaky"),
                    ("STATUS", "new"),
                    ("EVIDENCE", "note:474fa40ae4db fix the flaky test"),
                    ("EVIDENCE", "rt:PRRT_kwDO"),
                    ("ACTION", "constraint"),
                ),
                "LongNames": (("TITLE", "the names are long"), ("STATUS", "new"), ("EVIDENCE", "rt:PRRT")),
                "Ratified": (
                    ("TITLE", "already ratified"),
                    ("STATUS", "ratified"),
                    ("EVIDENCE", "note:474fa40ae4db"),
                    ("ACTION", "wave"),
                ),
            },
        )
        request = argparse.Namespace(all=False)

        # Act
        document = inbox_list(request, self.runtime)

        # Assert
        self.assertEqual(
            document["patterns"],
            [
                {
                    "name": "FlakyTests",
                    "action": "constraint",
                    "signals": [
                        "a4a5f464d8bb319accf7b46a8bf8e366b35f89e2598d104fce5192ffc52659bc",
                        "19757dd92a2f6de337f3946640b43670c28549c4efa10b5438feb15d3106d66f",
                    ],
                },
                {"name": "LongNames", "action": None, "signals": []},
            ],
        )


class InboxListOfSignalsSharingAKeyTest(unittest.TestCase):
    def test_should_group_the_listed_signals_by_the_keys_of_the_triage(self):
        # Arrange
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        runtime = create_test_runtime(create_test_paths(Path(directory.name)))
        signals = runtime.paths.state_root / "inbox" / "signals.jsonl"
        signals.parent.mkdir(parents=True)
        signals.write_text(
            '{"schema_version": 1, "ts": "2026-10-17T09:00:00Z", "event": "recorded", "kind": "review_thread",'
            ' "project": "oak", "fingerprint": "rt:101", "evidence": {"path": "brigade/cli.py"}}\n'
            '{"schema_version": 1, "ts": "2026-10-17T09:00:00Z", "event": "recorded", "kind": "review_thread",'
            ' "project": "oak", "fingerprint": "rt:102", "evidence": {"path": "brigade/cli.py"}}\n',
            encoding="utf-8",
        )
        request = argparse.Namespace(all=False)

        # Act
        document = inbox_list(request, runtime)

        # Assert
        self.assertEqual(
            document["families"],
            [
                {
                    "by": "file",
                    "key": "brigade/cli.py",
                    "signals": [
                        "cb358a1d6802f45160655a3b27b17a1bfd58f4fe6adba1c785d46bfe3beb051e",
                        "698b1dbbc546f21b357b8fdcb69ceea5144cf18aa4b8d264d9356d15c1ec2c61",
                    ],
                }
            ],
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
            "families": [],
            "patterns": [],
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
        document = {"schema_version": 1, "signals": [], "families": [], "patterns": []}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, "no signal in the inbox")

    def test_should_print_the_proposed_patterns_after_the_signals(self):
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
                }
            ],
            "families": [],
            "patterns": [
                {
                    "name": "FlakyTests",
                    "action": "constraint",
                    "signals": [
                        "a4a5f464d8bb319accf7b46a8bf8e366b35f89e2598d104fce5192ffc52659bc",
                        "19757dd92a2f6de337f3946640b43670c28549c4efa10b5438feb15d3106d66f",
                    ],
                },
                {"name": "LongNames", "action": None, "signals": []},
            ],
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "id       kind  project  count  age  status\n"
            "a4a5f46  note  oak      1      2d   new\n"
            "\n"
            "pattern     action      signals\n"
            "FlakyTests  constraint  a4a5f46 19757dd\n"
            "LongNames   -           -",
        )

    def test_should_print_the_proposed_patterns_of_an_inbox_without_new_signal(self):
        # Arrange
        document = {
            "schema_version": 1,
            "signals": [],
            "families": [],
            "patterns": [{"name": "LongNames", "action": "wave", "signals": []}],
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "no signal in the inbox\n\npattern    action  signals\nLongNames  wave    -",
        )
