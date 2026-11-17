import unittest

from brigade.ledger.wave_blocked import WaveBlocked


class WaveBlockedTest(unittest.TestCase):
    def test_should_read_a_wave_blocked_on_the_quota_until_its_resume(self):
        # Act
        event = WaveBlocked.from_document(
            {"event": "wave.blocked", "wave": "tidepool_w16", "reason": "quota", "resume_at": "2026-10-19T15:00:00Z"}
        )

        # Assert
        self.assertEqual(event, WaveBlocked(wave="tidepool_w16", reason="quota", resume_at="2026-10-19T15:00:00Z"))

    def test_should_write_a_wave_blocked_on_the_quota_until_its_resume(self):
        # Arrange
        event = WaveBlocked(wave="tidepool_w16", reason="quota", resume_at="2026-10-19T15:00:00Z")

        # Act
        document = event.to_document()

        # Assert
        self.assertEqual(document, {"wave": "tidepool_w16", "reason": "quota", "resume_at": "2026-10-19T15:00:00Z"})
