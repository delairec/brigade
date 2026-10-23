import unittest
from datetime import UTC, datetime

from brigade.errors import BrigadeError
from brigade.ledger.describe_wave import describe_wave
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.pr_merged import PrMerged
from brigade.ledger.read_ledger import LedgerReading
from brigade.ledger.task_parked import TaskParked
from brigade.ledger.wave_paused import WavePaused
from brigade.ledger.wave_resumed import WaveResumed
from brigade.ledger.wave_started import WaveStarted
from tests.unit.ledger.create_run_finished import create_run_finished


def at_minute(minute: int) -> datetime:
    return datetime(2026, 10, 10, 9, minute, tzinfo=UTC)


WAVE_W1 = LedgerReading(
    entries=(
        LedgerEntry(at_minute(0), WaveStarted(wave="w1", project="tidepool", branch="main", tasks=("TP1", "TP2"))),
        LedgerEntry(at_minute(1), create_run_finished("r1", segment=1, main_steps=10, wave="w1", task="TP1")),
        LedgerEntry(at_minute(2), WaveResumed(wave="w1", reason="stray")),
        LedgerEntry(at_minute(3), WavePaused(wave="w1", reason="quota", resume_at=None)),
        LedgerEntry(at_minute(4), WavePaused(wave="w1", reason="quota again", resume_at=None)),
        LedgerEntry(at_minute(5), WaveResumed(wave="w1", reason="quota reset")),
        LedgerEntry(at_minute(6), create_run_finished("r1", segment=2, main_steps=5, wave="w1", task="TP1")),
        LedgerEntry(at_minute(7), PrMerged(project="tidepool", wave="w1", task="TP1", pr=7, rounds=2, login=None)),
        LedgerEntry(at_minute(8), TaskParked(wave="w1", task="TP2", reason="blocked", blockers=("OPEN_QUESTION.Q1",))),
        LedgerEntry(at_minute(9), WavePaused(wave="w1", reason="forge account", resume_at=None)),
        LedgerEntry(at_minute(30), WaveStarted(wave="w2", project="tidepool", branch="main", tasks=("TP3",))),
    ),
    files=(),
    skipped=(),
)


class DescribeWaveTest(unittest.TestCase):
    def test_should_frame_the_wave_by_its_first_and_last_events(self):
        # Act
        wave = describe_wave(WAVE_W1, "w1")

        # Assert
        self.assertEqual(wave["first"], "2026-10-10T09:00:00Z")
        self.assertEqual(wave["last"], "2026-10-10T09:09:00Z")
        self.assertEqual(wave["wall_time_ms"], 540000)

    def test_should_pair_each_pause_with_the_resumption_ending_it(self):
        # Act
        wave = describe_wave(WAVE_W1, "w1")

        # Assert
        self.assertEqual(
            wave["pauses"],
            [
                {"paused_at": "2026-10-10T09:03:00Z", "resumed_at": "2026-10-10T09:05:00Z", "duration_ms": 120000},
                {"paused_at": "2026-10-10T09:09:00Z", "resumed_at": None, "duration_ms": None},
            ],
        )
        self.assertEqual(wave["paused_ms"], 120000)

    def test_should_tell_what_became_of_each_task(self):
        # Act
        wave = describe_wave(WAVE_W1, "w1")

        # Assert
        self.assertEqual(wave["tasks"], ["TP1", "TP2"])
        self.assertEqual(wave["pull_requests"], [{"task": "TP1", "pr": 7, "rounds": 2}])
        self.assertEqual(wave["hand_overs"], [{"task": "TP1", "role": "builder", "slot": "build", "segment": 2}])
        self.assertEqual(wave["parked"], ["TP2"])

    def test_should_summarize_the_steps_by_slot_and_by_role(self):
        # Act
        wave = describe_wave(WAVE_W1, "w1")

        # Assert
        self.assertEqual(list(wave["steps"]["by_slot"]), ["build"])
        self.assertEqual(list(wave["steps"]["by_role"]), ["builder"])
        self.assertEqual(
            wave["steps"]["by_slot"]["build"]["runs"],
            {"measured": 1, "unmeasured": 0, "p50": 15, "p90": 15, "partial": 0},
        )

    def test_should_refuse_a_wave_no_event_names(self):
        # Act
        with self.assertRaises(BrigadeError) as refusal:
            describe_wave(WAVE_W1, "w9")

        # Assert
        self.assertEqual(str(refusal.exception), "no event names the wave w9")


class DescribeWaveResumedTest(unittest.TestCase):
    def test_should_leave_no_pause_open_once_the_wave_resumed(self):
        # Arrange
        reading = LedgerReading(
            entries=(
                LedgerEntry(at_minute(0), WavePaused(wave="w1", reason="quota", resume_at=None)),
                LedgerEntry(at_minute(4), WaveResumed(wave="w1", reason="quota reset")),
            ),
            files=(),
            skipped=(),
        )

        # Act
        wave = describe_wave(reading, "w1")

        # Assert
        self.assertEqual(
            wave["pauses"],
            [{"paused_at": "2026-10-10T09:00:00Z", "resumed_at": "2026-10-10T09:04:00Z", "duration_ms": 240000}],
        )
