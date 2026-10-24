import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.inbox.read_inbox import Signal, read_inbox

NOW = datetime(2026, 10, 24, 9, 0, tzinfo=UTC)
NOTE_RECORDED_TWO_DAYS_AGO = (
    '{"schema_version": 1, "ts": "2026-10-22T09:00:00Z", "event": "recorded", "kind": "note", "project": "oak",'
    ' "fingerprint": "note:474fa40ae4db", "evidence": {"text": "fix the flaky test"}}\n'
)
THREAD_RECORDED_AN_HOUR_AGO = (
    '{"schema_version": 1, "ts": "2026-10-24T08:00:00Z", "event": "recorded", "kind": "review_thread",'
    ' "project": null, "fingerprint": "rt:PRRT_kwDO", "evidence": {"comment": "rename it"}}\n'
)
NOTE_RECORDED_AGAIN_A_MINUTE_AGO = (
    '{"schema_version": 1, "ts": "2026-10-24T08:59:00Z", "event": "recorded", "kind": "note", "project": "oak",'
    ' "fingerprint": "note:474fa40ae4db", "evidence": {"text": "fix the flaky test, again"}}\n'
)
NOTE_DISMISSED_A_DAY_AGO = (
    '{"schema_version": 1, "ts": "2026-10-23T09:00:00Z", "event": "dismissed", "fingerprint": "note:474fa40ae4db"}\n'
)


class ReadInboxTestCase(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.state_root = Path(directory.name) / "state"
        self.signals = self.state_root / "inbox" / "signals.jsonl"

    def write_signals(self, content: str) -> None:
        self.signals.parent.mkdir(parents=True)
        self.signals.write_text(content, encoding="utf-8")


class ReadInboxWhenNothingWasRecordedTest(ReadInboxTestCase):
    def test_should_read_no_signal(self):
        # Act
        signals = read_inbox(self.state_root, NOW)

        # Assert
        self.assertEqual(signals, ())


class ReadInboxOfSignalsRecordedSeveralTimesTest(ReadInboxTestCase):
    def test_should_fold_the_recordings_of_each_fingerprint_into_one_signal(self):
        # Arrange
        self.write_signals(NOTE_RECORDED_TWO_DAYS_AGO + THREAD_RECORDED_AN_HOUR_AGO + NOTE_RECORDED_AGAIN_A_MINUTE_AGO)

        # Act
        signals = read_inbox(self.state_root, NOW)

        # Assert
        self.assertEqual(
            signals,
            (
                Signal(
                    id="a4a5f464d8bb319accf7b46a8bf8e366b35f89e2598d104fce5192ffc52659bc",
                    fingerprint="note:474fa40ae4db",
                    kind="note",
                    project="oak",
                    count=2,
                    age_s=172800,
                    status="new",
                    evidence={"text": "fix the flaky test, again"},
                ),
                Signal(
                    id="19757dd92a2f6de337f3946640b43670c28549c4efa10b5438feb15d3106d66f",
                    fingerprint="rt:PRRT_kwDO",
                    kind="review_thread",
                    project=None,
                    count=1,
                    age_s=3600,
                    status="new",
                    evidence={"comment": "rename it"},
                ),
            ),
        )


class ReadInboxOfADismissedSignalTest(ReadInboxTestCase):
    def test_should_keep_the_signal_dismissed_when_it_is_recorded_again(self):
        # Arrange
        self.write_signals(NOTE_RECORDED_TWO_DAYS_AGO + NOTE_DISMISSED_A_DAY_AGO + NOTE_RECORDED_AGAIN_A_MINUTE_AGO)

        # Act
        signals = read_inbox(self.state_root, NOW)

        # Assert
        self.assertEqual(
            signals,
            (
                Signal(
                    id="a4a5f464d8bb319accf7b46a8bf8e366b35f89e2598d104fce5192ffc52659bc",
                    fingerprint="note:474fa40ae4db",
                    kind="note",
                    project="oak",
                    count=2,
                    age_s=172800,
                    status="dismissed",
                    evidence={"text": "fix the flaky test, again"},
                ),
            ),
        )


class ReadInboxOfALineItCannotReadTest(ReadInboxTestCase):
    def test_should_refuse_a_line_torn_by_a_crash_naming_its_file_and_its_number(self):
        # Arrange
        self.write_signals(THREAD_RECORDED_AN_HOUR_AGO + '{"schema_version": 1, "ts"\n')

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            read_inbox(self.state_root, NOW)

        # Assert
        self.assertEqual(str(refusal.exception), f"{self.signals}:2: is not JSON")

    def test_should_refuse_a_recording_without_its_fingerprint(self):
        # Arrange
        self.write_signals(
            '{"schema_version": 1, "ts": "2026-10-24T08:00:00Z", "event": "recorded", "kind": "note",'
            ' "project": null, "evidence": {}}\n'
        )

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            read_inbox(self.state_root, NOW)

        # Assert
        self.assertEqual(str(refusal.exception), f"{self.signals}:1: lacks the key fingerprint")

    def test_should_refuse_a_recording_without_its_kind(self):
        # Arrange
        self.write_signals(
            '{"schema_version": 1, "ts": "2026-10-24T08:00:00Z", "event": "recorded", "fingerprint": "rt:1",'
            ' "project": null, "evidence": {}}\n'
        )

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            read_inbox(self.state_root, NOW)

        # Assert
        self.assertEqual(str(refusal.exception), f"{self.signals}:1: lacks the key kind")

    def test_should_refuse_a_line_of_another_version(self):
        # Arrange
        self.write_signals(
            '{"schema_version": 2, "ts": "2026-10-24T08:00:00Z", "event": "dismissed", "fingerprint": "rt:1"}\n'
        )

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            read_inbox(self.state_root, NOW)

        # Assert
        self.assertEqual(str(refusal.exception), f"{self.signals}:1: schema_version is 2, not one of 1")

    def test_should_refuse_a_line_whose_ts_is_not_an_instant(self):
        # Arrange
        self.write_signals('{"schema_version": 1, "ts": "yesterday", "event": "dismissed", "fingerprint": "rt:1"}\n')

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            read_inbox(self.state_root, NOW)

        # Assert
        self.assertEqual(str(refusal.exception), f"{self.signals}:1: ts 'yesterday' is not an ISO 8601 UTC instant")

    def test_should_refuse_a_line_whose_ts_has_no_zone(self):
        # Arrange
        self.write_signals(
            '{"schema_version": 1, "ts": "2026-10-24T08:00:00", "event": "recorded", "kind": "note",'
            ' "project": null, "fingerprint": "rt:1", "evidence": {}}\n'
        )

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            read_inbox(self.state_root, NOW)

        # Assert
        self.assertEqual(
            str(refusal.exception), f"{self.signals}:1: ts '2026-10-24T08:00:00' is not an ISO 8601 UTC instant"
        )
