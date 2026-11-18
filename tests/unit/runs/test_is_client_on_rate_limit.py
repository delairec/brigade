import dataclasses
import unittest
from datetime import UTC, datetime

from brigade.ledger.ledger_entry import LedgerEntry
from brigade.runs.is_client_on_rate_limit import is_client_on_rate_limit
from brigade.system.reset_hour import ResetHour
from tests.unit.ledger.create_run_finished import create_run_finished

CUT_AT_EIGHT = datetime(2026, 10, 19, 8, 0, tzinfo=UTC)
BEFORE_THE_RESET = datetime(2026, 10, 19, 14, 0, tzinfo=UTC)
AFTER_THE_RESET = datetime(2026, 10, 19, 16, 0, tzinfo=UTC)
RESET_AT_THREE = ResetHour(hour="15:00", timezone="UTC")


def _create_cut(client: str) -> LedgerEntry:
    finished = dataclasses.replace(
        create_run_finished("20261019T070000Z-a1b2c3", client=client), error_class="rate_limit", reset=RESET_AT_THREE
    )
    return LedgerEntry(instant=CUT_AT_EIGHT, event=finished)


class IsClientOnRateLimitTest(unittest.TestCase):
    def test_should_hold_the_client_on_its_rate_limit_before_the_reset(self):
        # Act
        limited = is_client_on_rate_limit((_create_cut("claude-code"),), "claude-code", BEFORE_THE_RESET)

        # Assert
        self.assertTrue(limited)

    def test_should_release_the_client_from_the_reset_its_rate_limit_names(self):
        # Act
        limited = is_client_on_rate_limit((_create_cut("claude-code"),), "claude-code", AFTER_THE_RESET)

        # Assert
        self.assertFalse(limited)

    def test_should_ignore_the_rate_limit_of_another_client(self):
        # Act
        limited = is_client_on_rate_limit((_create_cut("vibe"),), "claude-code", BEFORE_THE_RESET)

        # Assert
        self.assertFalse(limited)

    def test_should_ignore_a_run_cut_on_another_error(self):
        # Arrange
        failed = LedgerEntry(
            instant=CUT_AT_EIGHT,
            event=dataclasses.replace(_create_cut("claude-code").event, error_class="execution"),
        )

        # Act
        limited = is_client_on_rate_limit((failed,), "claude-code", BEFORE_THE_RESET)

        # Assert
        self.assertFalse(limited)
