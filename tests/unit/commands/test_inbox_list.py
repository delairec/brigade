import argparse
import tempfile
import unittest
from pathlib import Path

from brigade.commands.inbox_list import COMMAND, inbox_list
from tests.unit.commands.command_runtime import create_corpus_double, write_ledger, write_operational_corpus
from tests.unit.commands.create_plugin_resolver import create_plugin_resolver
from tests.unit.commands.inbox_lines import NOTE_ON_OAK_RECORDED, THREAD_DISMISSED, THREAD_RECORDED
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.reports.document_plugin_double import DocumentPluginDouble
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
                        "stale": False,
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
                "answers": [],
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
                        "stale": False,
                    },
                    {
                        "id": "19757dd92a2f6de337f3946640b43670c28549c4efa10b5438feb15d3106d66f",
                        "fingerprint": "rt:PRRT_kwDO",
                        "kind": "review_thread",
                        "project": None,
                        "count": 1,
                        "age_s": 3600,
                        "status": "dismissed",
                        "stale": False,
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
                "answers": [],
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
                    "title": "the tests are flaky",
                    "action": "constraint",
                    "target": None,
                    "repeats": None,
                    "signals": [
                        "a4a5f464d8bb319accf7b46a8bf8e366b35f89e2598d104fce5192ffc52659bc",
                        "19757dd92a2f6de337f3946640b43670c28549c4efa10b5438feb15d3106d66f",
                    ],
                },
                {
                    "name": "LongNames",
                    "title": "the names are long",
                    "action": None,
                    "target": None,
                    "repeats": None,
                    "signals": [],
                },
            ],
        )

    def test_should_carry_the_target_of_a_pattern_and_the_name_of_the_pattern_it_repeats(self):
        # Arrange
        self.processes.answer_entities(
            self.runtime.paths.config_root,
            "PATTERN",
            {
                "FlakyTestsAgain": (
                    ("TITLE", "the tests are flaky again"),
                    ("STATUS", "new"),
                    ("ACTION", "constraint"),
                    ("TARGET", "tests/unit"),
                    ("REPEATS", "@PATTERN.FlakyTests"),
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
                    "name": "FlakyTestsAgain",
                    "title": "the tests are flaky again",
                    "action": "constraint",
                    "target": "tests/unit",
                    "repeats": "FlakyTests",
                    "signals": [],
                }
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
            "answers": [],
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
        document = {"schema_version": 1, "signals": [], "families": [], "patterns": [], "answers": []}

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
            "answers": [],
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
            "answers": [],
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "no signal in the inbox\n\npattern    action  signals\nLongNames  wave    -",
        )


class InboxListOfStudyAnswersTest(unittest.TestCase):
    def test_should_list_each_study_answer_with_its_study_and_its_project(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(root)
        (root / "config" / "answers.awawa").write_text("", encoding="utf-8")
        answer = {"type": "ANSWER", "name": "disk_20261019T090000Z_b2", "fields": [{"name": "STUDY", "value": "disk"}]}
        plugin = DocumentPluginDouble({str(root / "config" / "answers.awawa"): [answer]})
        no_study = {}
        runtime = create_test_runtime(
            create_test_paths(root),
            run_process=create_corpus_double(no_study),
            resolve_plugin=create_plugin_resolver({("progress_form", "awawa"): plugin}),
        )
        request = argparse.Namespace(all=False)

        # Act
        document = inbox_list(request, runtime)

        # Assert
        self.assertEqual(document["answers"], [{"id": "disk_20261019T090000Z_b2", "study": "disk", "project": None}])

    def test_should_print_the_study_answers_after_the_signals(self):
        # Arrange
        document = {
            "schema_version": 1,
            "signals": [],
            "families": [],
            "patterns": [],
            "answers": [{"id": "disk_20261019T090000Z_b2", "study": "disk", "project": None}],
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "no signal in the inbox\n\nanswer                    study  project\ndisk_20261019T090000Z_b2  disk   -",
        )


STALL_RECORDED = (
    '{"schema_version": 1, "ts": "2026-10-19T07:00:00Z", "event": "recorded", "kind": "stall", "project": "oak",'
    ' "fingerprint": "stall:oak:oak_w2:B17", "evidence": {"wave": "oak_w2", "task": "B17", "last_action": "running"}}\n'
)


class InboxListOfStallsTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.runtime = create_test_runtime(create_test_paths(self.root))
        signals = self.runtime.paths.state_root / "inbox" / "signals.jsonl"
        signals.parent.mkdir(parents=True)
        signals.write_text(STALL_RECORDED, encoding="utf-8")

    def write_last_state_of_the_task(self, state: str) -> None:
        write_ledger(
            self.root,
            [
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T07:30:00Z",
                    "event": "task.state",
                    "wave": "oak_w2",
                    "task": "B17",
                    "state": state,
                }
            ],
        )

    def test_should_mark_stale_a_stall_whose_task_merged_since(self):
        # Arrange
        self.write_last_state_of_the_task("merged")
        request = argparse.Namespace(all=False)

        # Act
        document = inbox_list(request, self.runtime)

        # Assert
        self.assertTrue(document["signals"][0]["stale"])

    def test_should_leave_a_stall_whose_task_is_not_merged_unmarked(self):
        # Arrange
        self.write_last_state_of_the_task("pr_open")
        request = argparse.Namespace(all=False)

        # Act
        document = inbox_list(request, self.runtime)

        # Assert
        self.assertFalse(document["signals"][0]["stale"])

    def test_should_leave_a_stall_whose_task_the_ledger_holds_no_state_of_unmarked(self):
        # Arrange
        request = argparse.Namespace(all=False)

        # Act
        document = inbox_list(request, self.runtime)

        # Assert
        self.assertFalse(document["signals"][0]["stale"])
