import dataclasses
import unittest
from datetime import UTC, datetime

from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.sum_quota_usage import sum_quota_usage
from brigade.ledger.wave_started import WaveStarted
from brigade.system.token_usage import TokenUsage
from tests.unit.ledger.create_run_finished import create_run_finished

NOW = datetime(2026, 10, 19, 9, 0, tzinfo=UTC)
FIVE_HOURS = 5


def at(hour: int, minute: int) -> datetime:
    return datetime(2026, 10, 19, hour, minute, tzinfo=UTC)


def create_reported_run(run: str, usage: TokenUsage):
    return dataclasses.replace(create_run_finished(run), usage=usage)


class SumQuotaUsageTest(unittest.TestCase):
    def test_should_sum_the_usage_of_the_runs_finished_within_the_window(self):
        # Arrange
        entries = (
            LedgerEntry(at(3, 59), create_reported_run("r0", TokenUsage(1000, 1000, 1000, 1000))),
            LedgerEntry(at(4, 0), create_reported_run("r1", TokenUsage(10, 20, 30, 40))),
            LedgerEntry(at(8, 30), create_reported_run("r2", TokenUsage(1, 2, 3, 4))),
            LedgerEntry(at(8, 40), WaveStarted(wave="w1", project="oak", branch="main", tasks=("B1",))),
        )

        # Act
        quota = sum_quota_usage(entries, NOW, FIVE_HOURS)

        # Assert
        self.assertEqual(
            quota,
            {
                "window_hours": 5,
                "usage": {
                    "input_tokens": 11,
                    "output_tokens": 22,
                    "cache_creation_input_tokens": 33,
                    "cache_read_input_tokens": 44,
                },
                "runs_without_usage": 0,
            },
        )

    def test_should_count_apart_the_runs_of_the_window_that_carry_no_usage(self):
        # Arrange
        entries = (
            LedgerEntry(at(2, 0), create_run_finished("r0")),
            LedgerEntry(at(5, 0), create_run_finished("r1")),
            LedgerEntry(at(6, 0), create_reported_run("r2", TokenUsage(1, 2, 3, 4))),
        )

        # Act
        quota = sum_quota_usage(entries, NOW, FIVE_HOURS)

        # Assert
        self.assertEqual(quota["runs_without_usage"], 1)

    def test_should_answer_zero_tokens_over_a_window_with_no_run(self):
        # Arrange
        no_entry = ()

        # Act
        quota = sum_quota_usage(no_entry, NOW, FIVE_HOURS)

        # Assert
        self.assertEqual(
            quota,
            {
                "window_hours": 5,
                "usage": {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cache_creation_input_tokens": 0,
                    "cache_read_input_tokens": 0,
                },
                "runs_without_usage": 0,
            },
        )
