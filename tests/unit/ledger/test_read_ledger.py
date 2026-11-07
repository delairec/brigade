import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from brigade.ledger.forge_account_unavailable import ForgeAccountUnavailable
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.read_ledger import LedgerReading, SkippedLine, read_ledger
from brigade.ledger.undeclared_event import UndeclaredEvent
from brigade.ledger.wave_paused import WavePaused
from brigade.ledger.wave_started import WaveStarted

WAVE_STARTED = (
    '{"schema_version": 2, "ts": "2026-09-30T22:00:00Z", "event": "wave.started", "wave": "tidepool_w16",'
    ' "project": "tidepool", "branch": "integration/M4-tides", "tasks": ["T7"]}\n'
)
WAVE_PAUSED = '{"schema_version": 1, "ts": "2026-10-01T00:15:00Z", "event": "wave.paused", "wave": "tidepool_w16", "reason": "quota", "resume_at": null}\n'
RUN_FINISHED_OF_SCHEMA_1 = (
    '{"schema_version": 1, "ts": "2026-10-07T10:33:00Z", "event": "run.finished", "run": "20261007T101817Z-2ee96f",'
    ' "segment": 1, "procedure": "awawa-task", "slot": "build", "role": "ada", "client": "claude-code",'
    ' "project": "brigade", "session": "857d4221", "steps": 40, "duration_ms": 19091, "usage": null,'
    ' "outcome": "done", "error_class": null, "exit": 0, "wave": null, "task": null,'
    ' "nulls": {"usage": "the client reported no usage"}}\n'
)
RUN_FINISHED_OF_SCHEMA_1_COUNTING_NO_STEPS = (
    '{"schema_version": 1, "ts": "2026-10-07T10:33:00Z", "event": "run.finished", "run": "20261007T101817Z-2ee96f",'
    ' "segment": 1, "procedure": "awawa-task", "slot": "build", "role": "ada", "client": "fake",'
    ' "project": "brigade", "session": "857d4221", "steps": null, "duration_ms": 19091, "usage": null,'
    ' "outcome": "done", "error_class": null, "exit": 0, "wave": null, "task": null,'
    ' "nulls": {"steps": "the client counts no steps", "usage": "the client reported no usage"}}\n'
)
RUN_FINISHED_OF_SCHEMA_2 = (
    '{"schema_version": 2, "ts": "2026-10-09T10:33:00Z", "event": "run.finished", "run": "20261009T101817Z-2ee96f",'
    ' "segment": 1, "procedure": "awawa-task", "slot": "build", "role": "ada", "client": "claude-code",'
    ' "project": "brigade", "session": "857d4221", "main_steps": 42, "total_steps": 54, "duration_ms": 900000,'
    ' "usage": null, "outcome": "done", "error_class": null, "exit": 0, "wave": null, "task": null,'
    ' "nulls": {"usage": "the client reported no usage"}, "cost_usd": 3.63}\n'
)
UNDECLARED_EVENT = '{"schema_version": 1, "ts": "2026-10-01T00:20:00Z", "event": "study.done", "study": "health"}\n'


class ReadLedgerTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.state_root = Path(self.root.name) / "brigade"
        self.ledger = self.state_root / "ledger"

    def tearDown(self):
        self.root.cleanup()

    def write_ledger(self, file_name: str, content: bytes) -> Path:
        ledger_file = self.ledger / file_name
        ledger_file.parent.mkdir(parents=True, exist_ok=True)
        ledger_file.write_bytes(content)
        return ledger_file


class ReadLedgerWhenNoLedgerWasWrittenTest(ReadLedgerTestCase):
    def test_should_read_nothing(self):
        # Act
        reading = read_ledger(self.state_root)

        # Assert
        self.assertEqual(reading, LedgerReading(entries=(), files=(), skipped=()))


class ReadLedgerWhenEveryLineIsWholeTest(ReadLedgerTestCase):
    def test_should_read_the_monthly_files_in_order_and_ignore_the_other_files(self):
        # Arrange
        october = self.write_ledger("2026-10.jsonl", (WAVE_PAUSED + UNDECLARED_EVENT).encode())
        september = self.write_ledger("2026-09.jsonl", WAVE_STARTED.encode())
        self.write_ledger("notes.txt", b"not a ledger file\n")

        # Act
        reading = read_ledger(self.state_root)

        # Assert
        self.assertEqual(
            reading,
            LedgerReading(
                entries=(
                    LedgerEntry(
                        instant=datetime(2026, 9, 30, 22, 0, tzinfo=UTC),
                        event=WaveStarted(
                            wave="tidepool_w16", project="tidepool", branch="integration/M4-tides", tasks=("T7",)
                        ),
                    ),
                    LedgerEntry(
                        instant=datetime(2026, 10, 1, 0, 15, tzinfo=UTC),
                        event=WavePaused(wave="tidepool_w16", reason="quota", resume_at=None),
                    ),
                    LedgerEntry(
                        instant=datetime(2026, 10, 1, 0, 20, tzinfo=UTC),
                        event=UndeclaredEvent(name="study.done"),
                    ),
                ),
                files=(str(september), str(october)),
                skipped=(),
            ),
        )


class ReadLedgerOfAForgeAccountUnavailableTest(ReadLedgerTestCase):
    def test_should_read_the_login_and_the_key_bound_to_it(self):
        # Arrange
        self.write_ledger(
            "2026-10.jsonl",
            b'{"schema_version": 1, "ts": "2026-10-09T12:30:00Z", "event": "forge_account.unavailable",'
            b' "login": "octo-bot", "key": "verify"}\n',
        )

        # Act
        reading = read_ledger(self.state_root)

        # Assert
        self.assertEqual(
            reading.entries,
            (
                LedgerEntry(
                    instant=datetime(2026, 10, 9, 12, 30, tzinfo=UTC),
                    event=ForgeAccountUnavailable(login="octo-bot", key="verify"),
                ),
            ),
        )


class ReadLedgerWhenTheLastLineWasNotEndedTest(ReadLedgerTestCase):
    def test_should_read_the_last_line_as_an_entry(self):
        # Arrange
        unended_last_line = WAVE_PAUSED.removesuffix("\n").encode()
        october = self.write_ledger("2026-10.jsonl", WAVE_STARTED.encode() + unended_last_line)

        # Act
        reading = read_ledger(self.state_root)

        # Assert
        self.assertEqual(
            reading,
            LedgerReading(
                entries=(
                    LedgerEntry(
                        instant=datetime(2026, 9, 30, 22, 0, tzinfo=UTC),
                        event=WaveStarted(
                            wave="tidepool_w16", project="tidepool", branch="integration/M4-tides", tasks=("T7",)
                        ),
                    ),
                    LedgerEntry(
                        instant=datetime(2026, 10, 1, 0, 15, tzinfo=UTC),
                        event=WavePaused(wave="tidepool_w16", reason="quota", resume_at=None),
                    ),
                ),
                files=(str(october),),
                skipped=(),
            ),
        )


class ReadLedgerWhenALineFailsItsEnvelopeTest(ReadLedgerTestCase):
    def test_should_skip_the_line_naming_its_file_its_number_and_the_reason(self):
        # Arrange
        rows = [
            (b'{"schema_version": 1, "ts": "2026-10-01T00:41\n', "not JSON"),
            (b"\xff\xfe\n", "not JSON"),
            (b"\n", "not JSON"),
            (b"[1, 2]\n", "the document is a list, not an object"),
            (
                b'{"ts": "2026-10-01T00:41:00Z", "event": "wave.paused", "wave": "tidepool_w16", "reason": "quota", "resume_at": null}\n',
                "lacks the key schema_version",
            ),
            (
                b'{"schema_version": 1, "event": "wave.paused", "wave": "tidepool_w16", "reason": "quota", "resume_at": null}\n',
                "lacks the key ts",
            ),
            (b'{"schema_version": 1, "ts": "2026-10-01T00:41:00Z", "wave": "tidepool_w16"}\n', "lacks the key event"),
            (
                b'{"schema_version": 2, "ts": "2026-10-01T00:41:00Z", "event": "wave.paused", "wave": "tidepool_w16", "reason": "quota", "resume_at": null}\n',
                "schema_version is 2, not one of 1",
            ),
            (
                b'{"schema_version": 1, "ts": "yesterday", "event": "wave.paused", "wave": "tidepool_w16", "reason": "quota", "resume_at": null}\n',
                "ts 'yesterday' is not an ISO 8601 UTC instant",
            ),
            (
                b'{"schema_version": 1, "ts": "2026-10-01T02:41:00+02:00", "event": "wave.paused", "wave": "tidepool_w16", "reason": "quota", "resume_at": null}\n',
                "ts '2026-10-01T02:41:00+02:00' is not an ISO 8601 UTC instant",
            ),
            (
                b'{"schema_version": 1, "ts": "2026-13-01T00:41:00Z", "event": "wave.paused", "wave": "tidepool_w16", "reason": "quota", "resume_at": null}\n',
                "ts '2026-13-01T00:41:00Z' is not an ISO 8601 UTC instant",
            ),
            (b'{"schema_version": 1, "ts": "2026-10-01T00:41:00Z", "event": "wave.paused"}\n', "lacks the key wave"),
            (
                b'{"schema_version": 3, "ts": "2026-10-01T00:41:00Z", "event": "run.finished", "run": "r1"}\n',
                "schema_version is 3, not one of 2",
            ),
            (
                (
                    b'{"schema_version": 1, "ts": "2026-10-01T00:41:00Z", "event": "wave.started", "wave": "M1",'
                    b' "project": "tidepool"}\n'
                ),
                "schema_version is 1, not one of 2",
            ),
            (
                (
                    b'{"schema_version": 1, "ts": "2026-10-01T00:41:00Z", "event": "task.state", "wave": "M1",'
                    b' "task": "S3", "state": "abandoned"}\n'
                ),
                (
                    "the task state abandoned is none of queued, running, pr_open, verifying, verified, merged,"
                    " changes_requested, fixing, parked, paused:quota"
                ),
            ),
        ]
        for content, expected_reason in rows:
            with self.subTest(content=content):
                # Arrange
                october = self.write_ledger("2026-10.jsonl", WAVE_PAUSED.encode() + content)

                # Act
                reading = read_ledger(self.state_root)

                # Assert
                self.assertEqual(
                    reading,
                    LedgerReading(
                        entries=(
                            LedgerEntry(
                                instant=datetime(2026, 10, 1, 0, 15, tzinfo=UTC),
                                event=WavePaused(wave="tidepool_w16", reason="quota", resume_at=None),
                            ),
                        ),
                        files=(str(october),),
                        skipped=(SkippedLine(file=str(october), line=2, reason=expected_reason),),
                    ),
                )


class ReadLedgerOfRunsFinishedTest(ReadLedgerTestCase):
    def test_should_skip_a_line_of_schema_1_naming_its_version(self):
        for line in [RUN_FINISHED_OF_SCHEMA_1, RUN_FINISHED_OF_SCHEMA_1_COUNTING_NO_STEPS]:
            with self.subTest(line=line):
                # Arrange
                october = self.write_ledger("2026-10.jsonl", line.encode())

                # Act
                reading = read_ledger(self.state_root)

                # Assert
                self.assertEqual(
                    reading,
                    LedgerReading(
                        entries=(),
                        files=(str(october),),
                        skipped=(SkippedLine(file=str(october), line=1, reason="schema_version is 1, not one of 2"),),
                    ),
                )

    def test_should_read_a_line_of_schema_2_with_its_cost(self):
        # Arrange
        self.write_ledger("2026-10.jsonl", RUN_FINISHED_OF_SCHEMA_2.encode())

        # Act
        reading = read_ledger(self.state_root)

        # Assert
        [entry] = reading.entries
        self.assertEqual(entry.event.main_steps, 42)
        self.assertEqual(entry.event.total_steps, 54)
        self.assertEqual(entry.event.cost_usd, 3.63)


class ReadLedgerSinceAnEarlierReadingTest(ReadLedgerTestCase):
    def test_should_add_the_lines_appended_since_to_the_entries_it_read_before(self):
        # Arrange
        october = self.write_ledger("2026-10.jsonl", WAVE_STARTED.encode())
        earlier = read_ledger(self.state_root)
        october.write_bytes(WAVE_STARTED.replace("tidepool_w16", "tidepool_w99").encode() + WAVE_PAUSED.encode())

        # Act
        reading = read_ledger(self.state_root, earlier)

        # Assert
        self.assertEqual(
            reading.entries,
            (
                LedgerEntry(
                    instant=datetime(2026, 9, 30, 22, 0, tzinfo=UTC),
                    event=WaveStarted(
                        wave="tidepool_w16", project="tidepool", branch="integration/M4-tides", tasks=("T7",)
                    ),
                ),
                LedgerEntry(
                    instant=datetime(2026, 10, 1, 0, 15, tzinfo=UTC),
                    event=WavePaused(wave="tidepool_w16", reason="quota", resume_at=None),
                ),
            ),
        )

    def test_should_number_a_line_skipped_since_after_the_lines_read_before(self):
        # Arrange
        october = self.write_ledger("2026-10.jsonl", WAVE_STARTED.encode())
        earlier = read_ledger(self.state_root)
        october.write_bytes(WAVE_STARTED.encode() + b"not json\n")

        # Act
        reading = read_ledger(self.state_root, earlier)

        # Assert
        self.assertEqual(reading.skipped, (SkippedLine(file=str(october), line=2, reason="not JSON"),))

    def test_should_read_a_line_completed_since_as_one_entry(self):
        # Arrange
        october = self.write_ledger("2026-10.jsonl", WAVE_STARTED.encode() + WAVE_PAUSED.encode()[:40])
        earlier = read_ledger(self.state_root)
        october.write_bytes(WAVE_STARTED.encode() + WAVE_PAUSED.encode())

        # Act
        reading = read_ledger(self.state_root, earlier)

        # Assert
        self.assertEqual(
            reading,
            LedgerReading(
                entries=(
                    LedgerEntry(
                        instant=datetime(2026, 9, 30, 22, 0, tzinfo=UTC),
                        event=WaveStarted(
                            wave="tidepool_w16", project="tidepool", branch="integration/M4-tides", tasks=("T7",)
                        ),
                    ),
                    LedgerEntry(
                        instant=datetime(2026, 10, 1, 0, 15, tzinfo=UTC),
                        event=WavePaused(wave="tidepool_w16", reason="quota", resume_at=None),
                    ),
                ),
                files=(str(october),),
                skipped=(),
            ),
        )

    def test_should_read_an_unended_last_line_once_after_it_was_ended(self):
        # Arrange
        october = self.write_ledger("2026-10.jsonl", WAVE_PAUSED.removesuffix("\n").encode())
        earlier = read_ledger(self.state_root)
        october.write_bytes(WAVE_PAUSED.encode() + b"not json\n")

        # Act
        reading = read_ledger(self.state_root, earlier)

        # Assert
        self.assertEqual(
            reading,
            LedgerReading(
                entries=(
                    LedgerEntry(
                        instant=datetime(2026, 10, 1, 0, 15, tzinfo=UTC),
                        event=WavePaused(wave="tidepool_w16", reason="quota", resume_at=None),
                    ),
                ),
                files=(str(october),),
                skipped=(SkippedLine(file=str(october), line=2, reason="not JSON"),),
            ),
        )

    def test_should_read_each_appended_line_once_over_successive_extensions(self):
        # Arrange
        october = self.write_ledger("2026-10.jsonl", WAVE_STARTED.encode())
        first = read_ledger(self.state_root)
        october.write_bytes(WAVE_STARTED.encode() + WAVE_PAUSED.encode())
        second = read_ledger(self.state_root, first)
        october.write_bytes(WAVE_STARTED.encode() + WAVE_PAUSED.encode() + b"not json\n")

        # Act
        reading = read_ledger(self.state_root, second)

        # Assert
        self.assertEqual(
            reading,
            LedgerReading(
                entries=(
                    LedgerEntry(
                        instant=datetime(2026, 9, 30, 22, 0, tzinfo=UTC),
                        event=WaveStarted(
                            wave="tidepool_w16", project="tidepool", branch="integration/M4-tides", tasks=("T7",)
                        ),
                    ),
                    LedgerEntry(
                        instant=datetime(2026, 10, 1, 0, 15, tzinfo=UTC),
                        event=WavePaused(wave="tidepool_w16", reason="quota", resume_at=None),
                    ),
                ),
                files=(str(october),),
                skipped=(SkippedLine(file=str(october), line=3, reason="not JSON"),),
            ),
        )

    def test_should_read_a_monthly_file_written_since_from_its_start(self):
        # Arrange
        self.write_ledger("2026-09.jsonl", WAVE_STARTED.encode())
        earlier = read_ledger(self.state_root)
        self.write_ledger("2026-10.jsonl", WAVE_PAUSED.encode())

        # Act
        reading = read_ledger(self.state_root, earlier)

        # Assert
        self.assertEqual(
            reading.entries,
            (
                LedgerEntry(
                    instant=datetime(2026, 9, 30, 22, 0, tzinfo=UTC),
                    event=WaveStarted(
                        wave="tidepool_w16", project="tidepool", branch="integration/M4-tides", tasks=("T7",)
                    ),
                ),
                LedgerEntry(
                    instant=datetime(2026, 10, 1, 0, 15, tzinfo=UTC),
                    event=WavePaused(wave="tidepool_w16", reason="quota", resume_at=None),
                ),
            ),
        )
