import dataclasses
import unittest
from datetime import UTC, datetime

from brigade.errors import BrigadeError
from brigade.ledger.describe_wave import describe_wave
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.pr_merged import PrMerged
from brigade.ledger.read_ledger import LedgerReading
from brigade.ledger.task_parked import TaskParked
from brigade.ledger.task_state import TaskState
from brigade.ledger.wave_paused import WavePaused
from brigade.ledger.wave_resumed import WaveResumed
from brigade.ledger.wave_started import WaveStarted
from brigade.system.token_usage import TokenUsage
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

    def test_should_summarize_the_runs_and_the_segments_of_each_role_an_unmeasured_segment_left_partial(self):
        # Arrange
        reading = LedgerReading(
            entries=(
                LedgerEntry(at_minute(0), create_run_finished("r1", segment=1, main_steps=10, wave="w1", task="TP1")),
                LedgerEntry(at_minute(1), create_run_finished("r1", segment=2, wave="w1", task="TP1")),
            ),
            files=(),
            skipped=(),
        )

        # Act
        wave = describe_wave(reading, "w1")

        # Assert
        self.assertEqual(
            wave["steps"]["by_role"],
            {
                "builder": {
                    "runs": {"measured": 1, "unmeasured": 0, "p50": 10, "p90": 10, "partial": 1},
                    "segments": {"measured": 1, "unmeasured": 1, "p50": 10, "p90": 10},
                }
            },
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


WAVE_W5 = LedgerReading(
    entries=(
        LedgerEntry(at_minute(0), WaveStarted(wave="w5", project="tidepool", branch="main", tasks=("TP5", "TP6"))),
        LedgerEntry(at_minute(20), create_run_finished("r6", main_steps=7, wave="w5", task="TP6")),
        LedgerEntry(at_minute(10), create_run_finished("r5", main_steps=30, wave="w5", task="TP5")),
        LedgerEntry(at_minute(11), TaskState(wave="w5", task="TP5", state="fixing")),
        LedgerEntry(at_minute(12), create_run_finished("r5b", segment=1, main_steps=4, wave="w5", task="TP5")),
        LedgerEntry(at_minute(13), TaskState(wave="w5", task="TP5", state="fixing")),
        LedgerEntry(
            at_minute(14),
            dataclasses.replace(
                create_run_finished("20261010T091300Z-ab12cd", main_steps=2, wave="w5", task="TP5"), slot="rebase"
            ),
        ),
    ),
    files=(),
    skipped=(),
)


class DescribeWaveOfEachTaskTest(unittest.TestCase):
    def test_should_count_the_repair_rounds_of_each_task_but_the_rebase_launches(self):
        # Act
        wave = describe_wave(WAVE_W5, "w5")

        # Assert
        self.assertEqual(wave["rounds_by_task"], {"TP5": 1})

    def test_should_sum_the_main_steps_of_the_runs_of_each_task(self):
        # Act
        wave = describe_wave(WAVE_W5, "w5")

        # Assert
        self.assertEqual(wave["steps_by_task"], {"TP5": 36, "TP6": 7})

    def test_should_leave_out_of_the_steps_by_task_a_run_of_the_wave_without_a_task(self):
        # Arrange
        reading = LedgerReading(
            entries=(
                LedgerEntry(at_minute(0), WaveStarted(wave="w6", project="tidepool", branch="main", tasks=("TP7",))),
                LedgerEntry(at_minute(1), create_run_finished("r7", main_steps=9, wave="w6", task="TP7")),
                LedgerEntry(at_minute(2), create_run_finished("r8", main_steps=4, wave="w6")),
            ),
            files=(),
            skipped=(),
        )

        # Act
        wave = describe_wave(reading, "w6")

        # Assert
        self.assertEqual(wave["steps_by_task"], {"TP7": 9})

    def test_should_date_each_entry_of_the_wave_oldest_first(self):
        # Arrange
        reading = LedgerReading(
            entries=(
                LedgerEntry(at_minute(5), TaskState(wave="w7", task="TP7", state="running")),
                LedgerEntry(at_minute(0), WaveStarted(wave="w7", project="tidepool", branch="main", tasks=("TP7",))),
            ),
            files=(),
            skipped=(),
        )

        # Act
        wave = describe_wave(reading, "w7")

        # Assert
        self.assertEqual(
            wave["timeline"],
            [
                {
                    "at": "2026-10-10T09:00:00Z",
                    "event": "wave.started",
                    "fields": {"wave": "w7", "project": "tidepool", "branch": "main", "tasks": ["TP7"]},
                },
                {
                    "at": "2026-10-10T09:05:00Z",
                    "event": "task.state",
                    "fields": {"wave": "w7", "task": "TP7", "state": "running"},
                },
            ],
        )


class DescribeWaveCostTest(unittest.TestCase):
    def setUp(self):
        self.reading = LedgerReading(
            entries=(
                LedgerEntry(at_minute(0), WaveStarted(wave="w3", project="tidepool", branch="main", tasks=("TP5",))),
                LedgerEntry(
                    at_minute(1),
                    create_run_finished(
                        "r5",
                        main_steps=30,
                        wave="w3",
                        task="TP5",
                        duration_ms=60000,
                        usage=TokenUsage(
                            input_tokens=1, output_tokens=2, cache_creation_input_tokens=3, cache_read_input_tokens=4
                        ),
                        cost_usd=3.5,
                    ),
                ),
                LedgerEntry(
                    at_minute(2), create_run_finished("r6", wave="w3", task="TP5", duration_ms=None, cost_usd=1.25)
                ),
                LedgerEntry(
                    at_minute(3),
                    create_run_finished(
                        "r7",
                        main_steps=8,
                        wave="w3",
                        task="TP6",
                        duration_ms=30000,
                        usage=TokenUsage(
                            input_tokens=10,
                            output_tokens=20,
                            cache_creation_input_tokens=30,
                            cache_read_input_tokens=40,
                        ),
                    ),
                ),
                LedgerEntry(at_minute(4), create_run_finished("r8", wave="w4", task="TP9", cost_usd=9.0)),
            ),
            files=(),
            skipped=(),
        )

    def test_should_sum_the_cost_and_the_tokens_of_the_runs_that_carry_them(self):
        # Act
        wave = describe_wave(self.reading, "w3")

        # Assert
        self.assertEqual(wave["cost_usd"], 4.75)
        self.assertEqual(
            wave["usage"],
            {"input_tokens": 11, "output_tokens": 22, "cache_creation_input_tokens": 33, "cache_read_input_tokens": 44},
        )

    def test_should_give_the_steps_duration_and_cost_of_each_task(self):
        # Act
        wave = describe_wave(self.reading, "w3")

        # Assert
        self.assertEqual(
            wave["by_task"],
            [
                {"task": "TP5", "steps": 30, "partial": False, "duration_ms": 60000, "cost_usd": 4.75},
                {"task": "TP6", "steps": 8, "partial": False, "duration_ms": 30000, "cost_usd": None},
            ],
        )

    def test_should_mark_partial_the_steps_of_a_task_whose_run_has_an_unmeasured_segment(self):
        # Arrange
        reading = LedgerReading(
            entries=(
                LedgerEntry(at_minute(0), create_run_finished("r9", segment=1, main_steps=40, wave="w5", task="TP8")),
                LedgerEntry(at_minute(1), create_run_finished("r9", segment=2, wave="w5", task="TP8")),
            ),
            files=(),
            skipped=(),
        )

        # Act
        wave = describe_wave(reading, "w5")

        # Assert
        self.assertEqual(
            wave["by_task"], [{"task": "TP8", "steps": 40, "partial": True, "duration_ms": 2000, "cost_usd": None}]
        )

    def test_should_give_no_cost_and_no_tokens_when_no_run_carries_them(self):
        # Act
        wave = describe_wave(WAVE_W1, "w1")

        # Assert
        self.assertIsNone(wave["cost_usd"])
        self.assertIsNone(wave["usage"])
