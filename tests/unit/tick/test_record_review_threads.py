import tempfile
import unittest
from pathlib import Path

from brigade.tick.record_review_threads import record_review_threads
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

THREADS = [
    {
        "thread": "PRRT_kw4a",
        "pull_request": 4,
        "path": "src/cart.py",
        "line": 12,
        "author": "delairec",
        "comment": "Name the total",
    },
    {
        "thread": "PRRT_kw4b",
        "pull_request": 4,
        "path": "src/cart.py",
        "line": 30,
        "author": "delairec",
        "comment": "Test the empty cart",
    },
]
THREAD_ALREADY_HELD = (
    '{"schema_version": 1, "ts": "2026-10-18T09:00:00Z", "event": "recorded", "kind": "review_thread",'
    ' "project": "oak", "fingerprint": "rt:PRRT_kw4a", "evidence": {"pull_request": 4, "path": "src/cart.py",'
    ' "line": 12, "author": "delairec", "comment": "Name the total"}}\n'
)


class RecordReviewThreadsTest(unittest.TestCase):
    def setUp(self):
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.runtime = create_test_runtime(create_test_paths(root))
        self.signals = root / "state" / "inbox" / "signals.jsonl"

    def test_should_record_each_review_thread_as_a_signal_fingerprinted_by_its_thread_id(self):
        # Act
        record_review_threads(self.runtime, "oak", THREADS)

        # Assert
        self.assertEqual(
            self.signals.read_text(encoding="utf-8"),
            '{"schema_version": 1, "ts": "2026-10-19T09:00:00Z", "event": "recorded", "kind": "review_thread",'
            ' "project": "oak", "fingerprint": "rt:PRRT_kw4a", "evidence": {"pull_request": 4, "path": "src/cart.py",'
            ' "line": 12, "author": "delairec", "comment": "Name the total"}}\n'
            '{"schema_version": 1, "ts": "2026-10-19T09:00:00Z", "event": "recorded", "kind": "review_thread",'
            ' "project": "oak", "fingerprint": "rt:PRRT_kw4b", "evidence": {"pull_request": 4, "path": "src/cart.py",'
            ' "line": 30, "author": "delairec", "comment": "Test the empty cart"}}\n',
        )

    def test_should_not_record_again_a_review_thread_the_inbox_already_holds(self):
        # Arrange
        self.signals.parent.mkdir(parents=True)
        self.signals.write_text(THREAD_ALREADY_HELD, encoding="utf-8")

        # Act
        record_review_threads(self.runtime, "oak", THREADS)

        # Assert
        self.assertEqual(
            self.signals.read_text(encoding="utf-8"),
            '{"schema_version": 1, "ts": "2026-10-18T09:00:00Z", "event": "recorded", "kind": "review_thread",'
            ' "project": "oak", "fingerprint": "rt:PRRT_kw4a", "evidence": {"pull_request": 4, "path": "src/cart.py",'
            ' "line": 12, "author": "delairec", "comment": "Name the total"}}\n'
            '{"schema_version": 1, "ts": "2026-10-19T09:00:00Z", "event": "recorded", "kind": "review_thread",'
            ' "project": "oak", "fingerprint": "rt:PRRT_kw4b", "evidence": {"pull_request": 4, "path": "src/cart.py",'
            ' "line": 30, "author": "delairec", "comment": "Test the empty cart"}}\n',
        )
