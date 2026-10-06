import json
import multiprocessing
import os
import tempfile
import unittest
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.ledger.append_event import LedgerEvent, LedgerEventRefused, append_event

PARIS_SUMMER_TIME = timezone(timedelta(hours=2))
PROCESS_COUNT = 4
EVENTS_PER_PROCESS = 50
PADDING_LONGER_THAN_A_PIPE_BUFFER = "x" * 20000


def append_wave_starts(state_root: Path, writer: int) -> None:
    for index in range(EVENTS_PER_PROCESS):
        append_event(
            state_root,
            LedgerEvent(
                name="wave.started",
                instant=datetime(2026, 10, 6, 9, 30, tzinfo=UTC),
                fields={
                    "wave": f"w{writer}-{index}",
                    "project": "tidepool",
                    "padding": PADDING_LONGER_THAN_A_PIPE_BUFFER,
                },
            ),
        )


class AppendEventTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.state_root = Path(self.root.name) / "state" / "brigade"
        self.ledger = self.state_root / "ledger"

    def tearDown(self):
        self.root.cleanup()


class AppendEventWhenTheEventIsDeclared(AppendEventTestCase):
    def test_should_create_the_ledger_and_append_the_versioned_line_to_the_month_file(self):
        # Arrange
        event = LedgerEvent(
            name="wave.started",
            instant=datetime(2026, 10, 6, 9, 30, tzinfo=UTC),
            fields={"wave": "tp/16", "project": "tidepool"},
        )

        # Act
        append_event(self.state_root, event)

        # Assert
        self.assertEqual(
            [json.loads(line) for line in (self.ledger / "2026-10.jsonl").read_text().splitlines()],
            [
                {
                    "schema_version": 1,
                    "ts": "2026-10-06T09:30:00Z",
                    "event": "wave.started",
                    "wave": "tp/16",
                    "project": "tidepool",
                }
            ],
        )

    def test_should_write_the_instant_in_utc_into_the_file_of_its_utc_month(self):
        # Arrange
        event = LedgerEvent(
            name="wave.paused",
            instant=datetime(2026, 10, 1, 1, 30, tzinfo=PARIS_SUMMER_TIME),
            fields={"wave": "tp/16"},
        )

        # Act
        append_event(self.state_root, event)

        # Assert
        self.assertEqual(
            json.loads((self.ledger / "2026-09.jsonl").read_text())["ts"],
            "2026-09-30T23:30:00Z",
        )

    def test_should_append_after_the_lines_already_written(self):
        # Arrange
        self.ledger.mkdir(parents=True)
        earlier_line = '{"schema_version": 1, "ts": "2026-10-01T08:00:00Z", "event": "wave.resumed", "wave": "tp/16"}\n'
        (self.ledger / "2026-10.jsonl").write_text(earlier_line)
        event = LedgerEvent(
            name="wave.paused",
            instant=datetime(2026, 10, 6, 9, 30, tzinfo=UTC),
            fields={"wave": "tp/16"},
        )

        # Act
        append_event(self.state_root, event)

        # Assert
        self.assertEqual(
            (self.ledger / "2026-10.jsonl").read_text(),
            earlier_line
            + '{"schema_version": 1, "ts": "2026-10-06T09:30:00Z", "event": "wave.paused", "wave": "tp/16"}\n',
        )


class AppendEventWhenTheEventIsRefused(AppendEventTestCase):
    def test_should_refuse_it_by_name_and_write_nothing(self):
        rows = [
            (
                "an undeclared name",
                LedgerEvent(
                    name="wave.exploded",
                    instant=datetime(2026, 10, 6, 9, 30, tzinfo=UTC),
                    fields={"wave": "tp/16"},
                ),
                "the event wave.exploded is not declared",
            ),
            (
                "a declared field missing",
                LedgerEvent(
                    name="pr.merged",
                    instant=datetime(2026, 10, 6, 9, 30, tzinfo=UTC),
                    fields={"project": "tidepool", "wave": "tp/16", "pr": 291},
                ),
                "the event pr.merged lacks task, rounds",
            ),
            (
                "a field named as the envelope",
                LedgerEvent(
                    name="wave.paused",
                    instant=datetime(2026, 10, 6, 9, 30, tzinfo=UTC),
                    fields={"wave": "tp/16", "ts": "2026-10-06T09:30:00Z"},
                ),
                "the event wave.paused carries the envelope key ts",
            ),
            (
                "an instant with no time zone",
                LedgerEvent(
                    name="wave.paused",
                    instant=datetime(2026, 10, 6, 9, 30),  # noqa: DTZ001 - the naive instant is the input refused
                    fields={"wave": "tp/16"},
                ),
                "the instant of the event wave.paused carries no time zone",
            ),
        ]
        for case, event, expected_message in rows:
            with self.subTest(case=case):
                # Act
                with self.assertRaises(LedgerEventRefused) as refusal:
                    append_event(self.state_root, event)

                # Assert
                self.assertEqual((str(refusal.exception), self.ledger.exists()), (expected_message, False))


class AppendEventFromSeveralProcesses(AppendEventTestCase):
    def test_should_leave_every_line_whole(self):
        # Arrange
        context = multiprocessing.get_context("fork")
        writers = [
            context.Process(target=append_wave_starts, args=(self.state_root, writer))
            for writer in range(PROCESS_COUNT)
        ]

        # Act
        for writer in writers:
            writer.start()
        for writer in writers:
            writer.join()

        # Assert
        lines = (self.ledger / "2026-10.jsonl").read_text().splitlines()
        self.assertEqual(len({json.loads(line)["wave"] for line in lines}), PROCESS_COUNT * EVENTS_PER_PROCESS)


@unittest.skipIf(os.geteuid() == 0, "root writes where the permissions refuse it")
class AppendEventWhereTheMachineRefusesTheWrite(AppendEventTestCase):
    def setUp(self):
        super().setUp()
        (self.state_root / "locks").mkdir(parents=True)
        self.event = LedgerEvent(
            name="wave.paused",
            instant=datetime(2026, 10, 6, 9, 30, tzinfo=UTC),
            fields={"wave": "tp/16"},
        )

    def tearDown(self):
        self.state_root.chmod(0o700)
        super().tearDown()

    def test_should_name_the_ledger_directory_it_cannot_create(self):
        # Arrange
        self.state_root.chmod(0o500)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            append_event(self.state_root, self.event)

        # Assert
        self.assertEqual(str(refusal.exception), f"cannot write {self.ledger}: Permission denied")

    def test_should_name_the_month_file_it_cannot_open(self):
        # Arrange
        self.ledger.mkdir()
        (self.ledger / "2026-10.jsonl").touch(mode=0o400)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            append_event(self.state_root, self.event)

        # Assert
        self.assertEqual(str(refusal.exception), f"cannot write {self.ledger / '2026-10.jsonl'}: Permission denied")
