import json
import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.studies.check_patterns import check_patterns
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.scripted_processes import ScriptedProcesses

FAMILIES = {
    "schema_version": 1,
    "collector": "inbox-families",
    "collected_at": "2026-10-25T09:00:00Z",
    "cache": False,
    "summary": {"families": 1, "signals": 2},
    "items": [
        {
            "by": "file",
            "key": "brigade/cli.py",
            "signals": [
                {"id": "cb358a1d", "fingerprint": "rt:101", "evidence": {"path": "brigade/cli.py"}},
                {"id": "89480cd0", "fingerprint": "rt:103", "evidence": {"path": "brigade/cli.py"}},
            ],
        }
    ],
}

OTHER_COLLECTION = {
    "schema_version": 1,
    "collector": "ledger",
    "collected_at": "2026-10-25T09:00:00Z",
    "cache": False,
    "summary": {"events": 1},
    "items": [{"signals": [{"fingerprint": "rt:102"}]}],
}


class CheckPatternsTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        self.processes = ScriptedProcesses()
        self.runtime = create_test_runtime(create_test_paths(root), run_process=self.processes)
        self.answer = root / "submitted"
        families = root / "families.json"
        families.write_text(json.dumps(FAMILIES), encoding="utf-8")
        self.collected = [{"collector": "inbox-families", "summary": FAMILIES["summary"], "document": str(families)}]
        self.other_collection = root / "ledger.json"
        self.other_collection.write_text(json.dumps(OTHER_COLLECTION), encoding="utf-8")

    def answer_patterns(self, patterns: dict) -> None:
        self.processes.answer_entities(self.answer, "PATTERN", patterns)

    def test_should_accept_new_patterns_citing_the_signals_collected_with_an_action(self):
        # Arrange
        self.answer_patterns(
            {
                "cli_is_hard_to_read": (
                    ("TITLE", "the cli is hard to read"),
                    ("STATUS", "new"),
                    ("EVIDENCE", "rt:101 a thread on brigade/cli.py"),
                    ("EVIDENCE", "rt:103"),
                    ("ACTION", "constraint"),
                )
            }
        )

        # Act
        accepted = check_patterns(self.runtime, self.answer, self.collected)

        # Assert
        self.assertIsNone(accepted)

    def test_should_refuse_a_pattern_that_is_not_new(self):
        # Arrange
        self.answer_patterns(
            {
                "cli_is_hard_to_read": (
                    ("TITLE", "the cli is hard to read"),
                    ("STATUS", "ratified"),
                    ("EVIDENCE", "rt:101"),
                    ("ACTION", "constraint"),
                )
            }
        )

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            check_patterns(self.runtime, self.answer, self.collected)

        # Assert
        self.assertEqual(str(refusal.exception), "@PATTERN.cli_is_hard_to_read is ratified: a triage proposes it new")

    def test_should_refuse_a_pattern_without_an_action(self):
        # Arrange
        self.answer_patterns(
            {"cli_is_hard_to_read": (("TITLE", "the cli is hard to read"), ("STATUS", "new"), ("EVIDENCE", "rt:101"))}
        )

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            check_patterns(self.runtime, self.answer, self.collected)

        # Assert
        self.assertEqual(str(refusal.exception), "@PATTERN.cli_is_hard_to_read names no ACTION")

    def test_should_refuse_a_pattern_citing_no_signal(self):
        # Arrange
        self.answer_patterns(
            {"cli_is_hard_to_read": (("TITLE", "the cli is hard to read"), ("STATUS", "new"), ("ACTION", "dismiss"))}
        )

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            check_patterns(self.runtime, self.answer, self.collected)

        # Assert
        self.assertEqual(str(refusal.exception), "@PATTERN.cli_is_hard_to_read holds no EVIDENCE")

    def test_should_refuse_an_evidence_opening_on_the_fingerprint_of_no_signal_collected(self):
        # Arrange
        self.answer_patterns(
            {
                "cli_is_hard_to_read": (
                    ("TITLE", "the cli is hard to read"),
                    ("STATUS", "new"),
                    ("EVIDENCE", "rt:10 a thread"),
                    ("ACTION", "constraint"),
                )
            }
        )

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            check_patterns(self.runtime, self.answer, self.collected)

        # Assert
        self.assertEqual(
            str(refusal.exception),
            "@PATTERN.cli_is_hard_to_read: the EVIDENCE 'rt:10 a thread' opens on the fingerprint of no signal"
            " inbox-families collected",
        )

    def test_should_refuse_an_evidence_opening_on_a_fingerprint_another_collector_collected(self):
        # Arrange
        self.answer_patterns(
            {
                "planner_is_hard_to_read": (
                    ("TITLE", "the planner is hard to read"),
                    ("STATUS", "new"),
                    ("EVIDENCE", "rt:102"),
                    ("ACTION", "constraint"),
                )
            }
        )
        collected_by_two_collectors = [
            *self.collected,
            {"collector": "ledger", "summary": OTHER_COLLECTION["summary"], "document": str(self.other_collection)},
        ]

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            check_patterns(self.runtime, self.answer, collected_by_two_collectors)

        # Assert
        self.assertEqual(
            str(refusal.exception),
            "@PATTERN.planner_is_hard_to_read: the EVIDENCE 'rt:102' opens on the fingerprint of no signal"
            " inbox-families collected",
        )
