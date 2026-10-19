import unittest
from datetime import UTC, datetime, timedelta, timezone

from brigade.system.reset_hour import ResetHour
from brigade.tick.decide_resume_at import decide_resume_at

NOW = datetime(2026, 10, 19, 12, 0, tzinfo=UTC)
NO_RESET = None
PARIS_CLOCK = timezone(timedelta(hours=2))


class DecideResumeAtTest(unittest.TestCase):
    def test_should_resume_at_the_first_instant_after_the_clock_at_the_hour_of_the_reset(self):
        for case, now, reset, expected in [
            (
                "later the same day",
                NOW,
                ResetHour(hour="15:00", timezone="UTC"),
                datetime(2026, 10, 19, 15, 0, tzinfo=UTC),
            ),
            (
                "earlier, so the next day",
                NOW,
                ResetHour(hour="09:30", timezone="UTC"),
                datetime(2026, 10, 20, 9, 30, tzinfo=UTC),
            ),
            (
                "at the clock itself, so the next day",
                NOW,
                ResetHour(hour="12:00", timezone="UTC"),
                datetime(2026, 10, 20, 12, 0, tzinfo=UTC),
            ),
            (
                "in the timezone the reset names",
                NOW,
                ResetHour(hour="15:00", timezone="Europe/Paris"),
                datetime(2026, 10, 19, 13, 0, tzinfo=UTC),
            ),
            (
                "in the timezone of the clock when the reset names none",
                NOW.astimezone(PARIS_CLOCK),
                ResetHour(hour="15:00", timezone=None),
                datetime(2026, 10, 19, 13, 0, tzinfo=UTC),
            ),
        ]:
            with self.subTest(case=case):
                # Act
                resume_at = decide_resume_at(now, reset)

                # Assert
                self.assertEqual(resume_at, expected)

    def test_should_resume_thirty_minutes_after_the_clock_when_the_result_names_no_reset(self):
        # Act
        resume_at = decide_resume_at(NOW, NO_RESET)

        # Assert
        self.assertEqual(resume_at, datetime(2026, 10, 19, 12, 30, tzinfo=UTC))
